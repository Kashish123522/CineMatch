"""
CineMatch - User Taste Profile ("Movie DNA")
Constructs initial user DNA vectors from onboarding preferences,
applies incremental interaction updates with exponential recency decay,
and generates human-readable Movie DNA summaries.
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.ml.features import ALL_MOODS, ProcessedFeatures

DEFAULT_HALF_LIFE_DAYS = 14.0

DEFAULT_INTERACTION_WEIGHTS = {
    "like": 1.0,
    "dislike": -1.0,
    "watched": 0.6,
    "skip": -0.4,
}


@dataclass
class UserInteraction:
    """Represents a single user interaction with a movie."""
    movie_id: int
    interaction_type: str  # 'like', 'dislike', 'rating', 'watched', 'skip'
    rating: Optional[float] = None  # 1.0 - 5.0 (for 'rating' type)
    timestamp: Optional[float] = None  # Unix timestamp in seconds


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """Normalize 1D vector to unit L2 norm."""
    norm = np.linalg.norm(vec)
    if norm == 0 or np.isnan(norm):
        return vec
    return vec / norm


def create_initial_profile_vector(
    features: ProcessedFeatures,
    liked_movie_ids: Optional[List[int]] = None,
    preferred_genres: Optional[List[str]] = None,
    preferred_languages: Optional[List[str]] = None,
    preferred_moods: Optional[List[str]] = None,
) -> np.ndarray:
    """
    Build the initial Movie DNA profile vector in the exact same feature space as movies.
    Combines liked seed movies with explicit onboarding preferences.
    """
    dim = features.feature_dim
    movie_vec_sum = np.zeros(dim, dtype=np.float32)
    movie_count = 0

    if liked_movie_ids:
        for mid in liked_movie_ids:
            v = features.get_movie_vector(mid)
            if v is not None:
                movie_vec_sum += v
                movie_count += 1

    liked_vec = _l2_normalize(movie_vec_sum / movie_count) if movie_count > 0 else None

    # Construct explicit preference vector
    explicit_vec = np.zeros(dim, dtype=np.float32)
    has_explicit = False

    # 1. Preferred genres
    if preferred_genres and "genres" in features.feature_slices:
        start, end = features.feature_slices["genres"]
        valid_genres = [g for g in preferred_genres if g in features.mlb_genres.classes_]
        if valid_genres:
            g_encoded = features.mlb_genres.transform([valid_genres])[0]
            if np.sum(g_encoded) > 0:
                explicit_vec[start:end] = g_encoded
                has_explicit = True

    # 2. Preferred moods
    if preferred_moods and "moods" in features.feature_slices:
        start, end = features.feature_slices["moods"]
        valid_moods = [m for m in preferred_moods if m in features.mlb_moods.classes_]
        if valid_moods:
            m_encoded = features.mlb_moods.transform([valid_moods])[0]
            if np.sum(m_encoded) > 0:
                explicit_vec[start:end] = m_encoded
                has_explicit = True

    # 3. Preferred languages
    if preferred_languages and "languages" in features.feature_slices:
        start, end = features.feature_slices["languages"]
        valid_langs = [l.lower() for l in preferred_languages if l.lower() in features.mlb_languages.classes_]
        if valid_langs:
            l_encoded = features.mlb_languages.transform([[lang] for lang in valid_langs])
            l_sum = np.sum(l_encoded, axis=0)
            if np.sum(l_sum) > 0:
                explicit_vec[start:end] = l_sum
                has_explicit = True

    explicit_vec = _l2_normalize(explicit_vec) if has_explicit else None

    # Blend liked movies + explicit preferences
    if liked_vec is not None and explicit_vec is not None:
        combined = 0.55 * liked_vec + 0.45 * explicit_vec
        return _l2_normalize(combined)
    elif liked_vec is not None:
        return liked_vec
    elif explicit_vec is not None:
        return explicit_vec
    else:
        # Fallback to mean across all movies
        mean_all = np.mean(features.feature_matrix, axis=0)
        return _l2_normalize(mean_all)


def calculate_interaction_weight(
    interaction: UserInteraction,
    reference_time: float,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """
    Calculate recency-decayed weight for an interaction.
    Dislikes are negative. Decays exponentially according to half_life_days.
    """
    itype = interaction.interaction_type.lower()

    if itype == "rating":
        # Scale 1-5 to [-1.0, 1.0] centered at 3.0
        r = interaction.rating if interaction.rating is not None else 3.0
        r = max(1.0, min(5.0, float(r)))
        base_weight = (r - 3.0) / 2.0
    else:
        base_weight = DEFAULT_INTERACTION_WEIGHTS.get(itype, 0.0)

    # Recency decay
    if interaction.timestamp is not None and half_life_days > 0:
        elapsed_seconds = max(0.0, reference_time - interaction.timestamp)
        elapsed_days = elapsed_seconds / 86400.0
        decay = math.pow(0.5, elapsed_days / half_life_days)
    else:
        decay = 1.0

    return base_weight * decay


def update_profile_vector(
    current_profile: np.ndarray,
    interactions: List[UserInteraction],
    features: ProcessedFeatures,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    learning_rate: float = 0.25,
    reference_time: Optional[float] = None,
) -> np.ndarray:
    """
    Update profile vector with a list of interactions using exponential recency decay.
    Positive interactions pull the vector closer; dislikes/negative ratings push it away.
    """
    if not interactions:
        return current_profile.copy()

    ref_time = (
        reference_time
        if reference_time is not None
        else max((i.timestamp or time.time()) for i in interactions)
    )

    delta_vec = np.zeros_like(current_profile)

    for inter in interactions:
        m_vec = features.get_movie_vector(inter.movie_id)
        if m_vec is None:
            continue
        eff_weight = calculate_interaction_weight(inter, reference_time=ref_time, half_life_days=half_life_days)
        delta_vec += eff_weight * m_vec

    updated = current_profile + (learning_rate * delta_vec)
    return _l2_normalize(updated)


def get_movie_dna_summary(
    profile_vector: np.ndarray,
    features: ProcessedFeatures,
    recent_interactions: Optional[List[UserInteraction]] = None,
    top_k: int = 4,
) -> Dict[str, Any]:
    """
    Generate a human-readable Movie DNA summary from profile vector & interactions.
    Includes top genres, moods, languages, directors/cast affinities, typical runtime, and recent trends.
    """
    # 1. Top Genres
    top_genres = []
    if "genres" in features.feature_slices:
        start, end = features.feature_slices["genres"]
        genre_scores = profile_vector[start:end]
        genre_classes = features.mlb_genres.classes_
        top_idx = np.argsort(genre_scores)[::-1][:top_k]
        total_top = max(1e-6, sum(genre_scores[i] for i in top_idx if genre_scores[i] > 0))
        for i in top_idx:
            val = float(genre_scores[i])
            if val > 0.01:
                pct = int(round((val / total_top) * 100))
                top_genres.append({"genre": str(genre_classes[i]), "affinity": round(val, 3), "percentage": pct})

    # 2. Top Moods
    top_moods = []
    if "moods" in features.feature_slices:
        start, end = features.feature_slices["moods"]
        mood_scores = profile_vector[start:end]
        mood_classes = features.mlb_moods.classes_
        top_m_idx = np.argsort(mood_scores)[::-1][:top_k]
        for i in top_m_idx:
            val = float(mood_scores[i])
            if val > 0.01:
                top_moods.append({"mood": str(mood_classes[i]), "affinity": round(val, 3)})

    # 3. Top Languages
    top_languages = []
    if "languages" in features.feature_slices:
        start, end = features.feature_slices["languages"]
        lang_scores = profile_vector[start:end]
        lang_classes = features.mlb_languages.classes_
        top_l_idx = np.argsort(lang_scores)[::-1][:3]
        for i in top_l_idx:
            val = float(lang_scores[i])
            if val > 0.01:
                top_languages.append(str(lang_classes[i]))

    # 4. Top Cast / Directors
    top_talent = []
    if "cast_director" in features.feature_slices:
        start, end = features.feature_slices["cast_director"]
        talent_scores = profile_vector[start:end]
        talent_names = features.cv_cast_director.get_feature_names_out()
        top_t_idx = np.argsort(talent_scores)[::-1][:top_k]
        for i in top_t_idx:
            val = float(talent_scores[i])
            if val > 0.01:
                clean_name = str(talent_names[i]).replace("_", " ").title()
                if "dicaprio" in str(talent_names[i]).lower():
                    clean_name = clean_name.replace("Dicaprio", "DiCaprio")
                top_talent.append(clean_name)

    # 5. Inferred typical runtime & intensity
    typical_runtime = 120
    if "numerical" in features.feature_slices:
        start, _ = features.feature_slices["numerical"]
        scaled_runtime = float(profile_vector[start])
        # de-normalize approximately using scaler
        min_rt = float(features.scaler_num.data_min_[0])
        max_rt = float(features.scaler_num.data_max_[0])
        approx_rt = min_rt + (scaled_runtime * (max_rt - min_rt))
        typical_runtime = int(round(max(70, min(220, approx_rt))))

    top_mood_names = [m["mood"] for m in top_moods[:2]]
    if any(m in ["dark", "thrilling"] for m in top_mood_names):
        typical_intensity = "Intense / Gripping"
    elif any(m in ["feel-good", "funny"] for m in top_mood_names):
        typical_intensity = "Light & Engaging"
    else:
        typical_intensity = "Medium / Thoughtful"

    # 6. Recent Trend Section
    trend_summary = "Seed profile based on onboarding preferences."
    if recent_interactions:
        # Sort interactions descending by timestamp
        sorted_inter = sorted(
            recent_interactions,
            key=lambda x: x.timestamp or 0.0,
            reverse=True,
        )
        recent_likes = []
        recent_skips_dislikes = []

        for item in sorted_inter[:6]:
            row = features.movies_df[features.movies_df["id"] == item.movie_id]
            title = row["title"].values[0] if not row.empty else f"Movie #{item.movie_id}"
            if item.interaction_type in ["like", "watched"] or (item.rating and item.rating >= 4.0):
                recent_likes.append(title)
            elif item.interaction_type in ["dislike", "skip"] or (item.rating and item.rating <= 2.0):
                recent_skips_dislikes.append(title)

        parts = []
        if recent_likes:
            parts.append(f"gravitating toward titles like {', '.join(recent_likes[:2])}")
        if recent_skips_dislikes:
            parts.append(f"cooling off on {', '.join(recent_skips_dislikes[:2])}")
        if parts:
            raw_summary = "; ".join(parts)
            trend_summary = raw_summary[0].upper() + raw_summary[1:] + "."

    return {
        "top_genres": top_genres,
        "top_moods": top_moods,
        "top_languages": top_languages or ["en"],
        "top_directors_actors": top_talent,
        "typical_runtime_minutes": typical_runtime,
        "typical_intensity": typical_intensity,
        "recent_trend": trend_summary,
    }
