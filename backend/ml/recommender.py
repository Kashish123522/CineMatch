"""
CineMatch - Multi-Objective Recommender Engine
Implements candidate generation, situational context scoring, recent behaviour scoring,
simplified collaborative filtering, and MMR diversity re-ranking.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import logging
import numpy as np
import pandas as pd
import yaml

from backend.ml.features import ProcessedFeatures
from backend.ml.profile import UserInteraction

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class SessionContext:
    """Situational context for 'what should THIS user watch RIGHT NOW?'"""
    time_available_minutes: Optional[int] = None
    mood: Optional[str] = None  # feel-good, dark, thrilling, romantic, thoughtful, funny, inspiring
    company: Optional[str] = None  # solo, date_night, family, friends
    intensity: Optional[str] = None  # light, medium, intense
    complexity: Optional[str] = None  # easy, moderate, complex
    language: Optional[str] = None  # en, ja, any, etc.
    unseen_only: bool = True  # If True, exclude all watched, liked, rated, and disliked movies


@dataclass
class RecommendationItem:
    """Structured recommendation result with score breakdowns."""
    movie_id: int
    title: str
    final_score: float
    score_breakdown: Dict[str, float]
    metadata: Dict[str, Any]


class SimpleCollaborativeModel:
    """
    Item-item co-occurrence collaborative scoring.
    Remains dormant (is_active = False, score = 0) until sufficient interaction data exists.
    """
    def __init__(self, min_system_interactions: int = 20):
        self.min_system_interactions = min_system_interactions
        self.item_cooccurrence: Dict[int, Dict[int, float]] = {}
        self.total_interactions: int = 0
        self.is_active: bool = False

    def fit(self, user_interactions: List[Tuple[int, int, float]]) -> None:
        """
        Fit co-occurrence matrix from (user_id, movie_id, weight) tuples.
        Only positive interactions (weight > 0) are used for co-occurrence.
        """
        self.total_interactions = len(user_interactions)
        if self.total_interactions < self.min_system_interactions:
            self.is_active = False
            return

        # Group by user
        user_likes: Dict[int, Set[int]] = {}
        for uid, mid, w in user_interactions:
            if w > 0:
                user_likes.setdefault(uid, set()).add(mid)

        # Build co-occurrence
        self.item_cooccurrence = {}
        for uid, items in user_likes.items():
            item_list = list(items)
            for i in range(len(item_list)):
                m1 = item_list[i]
                self.item_cooccurrence.setdefault(m1, {})
                for j in range(i + 1, len(item_list)):
                    m2 = item_list[j]
                    self.item_cooccurrence.setdefault(m2, {})
                    self.item_cooccurrence[m1][m2] = self.item_cooccurrence[m1].get(m2, 0.0) + 1.0
                    self.item_cooccurrence[m2][m1] = self.item_cooccurrence[m2].get(m1, 0.0) + 1.0

        self.is_active = True

    def fit_from_movielens(
        self,
        ratings_csv: Path | str,
        links_csv: Path | str,
        valid_tmdb_ids: Optional[Set[int]] = None,
    ) -> int:
        """
        Fit co-occurrence matrix from real MovieLens ratings mapped through links.csv.
        Only positive ratings (rating >= 3.5) are used to build item co-occurrences.
        """
        r_path = Path(ratings_csv)
        l_path = Path(links_csv)
        if not r_path.exists() or not l_path.exists():
            self.is_active = False
            return 0

        try:
            df_links = pd.read_csv(l_path).dropna(subset=["tmdbId"])
            df_links["tmdb_id"] = df_links["tmdbId"].astype(int)
            df_ratings = pd.read_csv(r_path)

            merged = df_ratings.merge(df_links[["movieId", "tmdb_id"]], on="movieId", how="inner")
            if valid_tmdb_ids:
                merged = merged[merged["tmdb_id"].isin(valid_tmdb_ids)]

            positives = merged[merged["rating"] >= 3.5]
            self.total_interactions = len(positives)
            if self.total_interactions < self.min_system_interactions:
                self.is_active = False
                return 0

            user_items = positives.groupby("userId")["tmdb_id"].apply(set).to_dict()
            self.item_cooccurrence = {}

            for uid, items in user_items.items():
                item_list = list(items)
                if len(item_list) > 300:
                    item_list = item_list[:300]
                for i in range(len(item_list)):
                    m1 = item_list[i]
                    if m1 not in self.item_cooccurrence:
                        self.item_cooccurrence[m1] = {}
                    for j in range(i + 1, min(len(item_list), i + 60)):
                        m2 = item_list[j]
                        self.item_cooccurrence[m1][m2] = self.item_cooccurrence[m1].get(m2, 0.0) + 1.0
                        if m2 not in self.item_cooccurrence:
                            self.item_cooccurrence[m2] = {}
                        self.item_cooccurrence[m2][m1] = self.item_cooccurrence[m2].get(m1, 0.0) + 1.0

            self.is_active = True
            return self.total_interactions
        except Exception:
            self.is_active = False
            return 0

    def score_candidate(self, candidate_id: int, user_liked_ids: List[int]) -> float:
        """Score candidate movie by co-occurrence similarity with user's liked movies."""
        if not self.is_active or not user_liked_ids:
            return 0.0

        cooccur_map = self.item_cooccurrence.get(candidate_id, {})
        if not cooccur_map:
            return 0.0

        matches = [cooccur_map.get(mid, 0.0) for mid in user_liked_ids]
        raw_score = sum(matches)
        # Normalize to [0.0, 1.0] with diminishing returns
        return float(np.tanh(raw_score / 3.0))


def load_recommender_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load config with safe defaults."""
    c_path = Path(config_path)
    if c_path.exists():
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {
        "ranking": {
            "weights": {
                "profile_similarity": 0.35,
                "recent_behavior": 0.20,
                "context_match": 0.25,
                "collaborative_score": 0.10,
                "quality_prior": 0.10,
            },
            "mmr": {"enabled": True, "lambda_param": 0.7, "top_k": 20},
        },
        "collaborative_filtering": {"min_system_interactions": 20},
    }


def compute_context_score(
    movie_row: pd.Series,
    context: Optional[SessionContext],
) -> Tuple[float, Dict[str, float]]:
    """
    Score situational context match in [0.0, 1.0].
    Returns (overall_context_score, sub_scores).
    """
    if context is None:
        return 1.0, {"runtime": 1.0, "mood": 1.0, "company": 1.0, "intensity": 1.0, "language": 1.0}

    # 1. Company mature filter check
    company = (context.company or "").lower()
    if company in ["family", "kids"]:
        is_family_anim = any(g in ["Animation", "Family"] for g in movie_row.get("genres_list", []))
        if not is_family_anim:
            if (
                movie_row.get("intensity") == "intense"
                or "dark" in movie_row.get("moods", [])
                or any(g in ["Horror", "Crime", "War"] for g in movie_row.get("genres_list", []))
            ):
                return 0.0, {"runtime": 0.0, "mood": 0.0, "company": 0.0, "intensity": 0.0, "language": 0.0}

    # 2. Runtime fit
    runtime = float(movie_row.get("runtime", 100.0))
    if context.time_available_minutes:
        limit = float(context.time_available_minutes)
        if runtime <= limit:
            score_runtime = 1.0
        elif runtime <= limit + 15:
            score_runtime = 0.75  # Grace buffer
        else:
            score_runtime = max(0.0, 1.0 - ((runtime - limit) / 60.0))
    else:
        score_runtime = 1.0

    # 3. Mood match using continuous mood scores
    if context.mood:
        target_mood = context.mood.lower().strip()
        mood_scores = movie_row.get("mood_scores", {})
        if isinstance(mood_scores, dict) and target_mood in mood_scores:
            score_mood = float(mood_scores[target_mood])
        else:
            movie_moods = [m.lower() for m in movie_row.get("moods", [])]
            score_mood = 1.0 if target_mood in movie_moods else 0.20
    else:
        score_mood = 1.0

    # 4. Company suitability
    if company in ["date_night", "date"]:
        genres = movie_row.get("genres_list", [])
        moods = movie_row.get("moods", [])
        if any(g in ["Romance", "Comedy", "Drama"] for g in genres) or "romantic" in moods:
            score_company = 1.0
        elif "dark" in moods:
            score_company = 0.3
        else:
            score_company = 0.7
    elif company in ["family", "kids"]:
        if "feel-good" in movie_row.get("moods", []) or any(
            g in ["Animation", "Family", "Adventure"] for g in movie_row.get("genres_list", [])
        ):
            score_company = 1.0
        else:
            score_company = 0.6
    elif company in ["friends"]:
        if any(g in ["Action", "Comedy", "Thriller"] for g in movie_row.get("genres_list", [])):
            score_company = 1.0
        else:
            score_company = 0.7
    else:
        score_company = 1.0

    # 5. Intensity & Complexity fit
    score_intensity = 1.0
    if context.intensity:
        cur_int = movie_row.get("intensity", "medium")
        if cur_int == context.intensity:
            score_intensity = 1.0
        elif "medium" in [cur_int, context.intensity]:
            score_intensity = 0.6
        else:
            score_intensity = 0.2

    # 6. Language fit
    score_language = 1.0
    if context.language and context.language.lower() != "any":
        movie_lang = str(movie_row.get("original_language", "en")).lower()
        score_language = 1.0 if movie_lang == context.language.lower() else 0.15

    sub_scores = {
        "runtime": score_runtime,
        "mood": score_mood,
        "company": score_company,
        "intensity": score_intensity,
        "language": score_language,
    }

    if context.mood:
        # High mood weighting when user picked Tonight's Vibe mood
        if context.language and context.language.lower() != "any":
            overall = (
                0.45 * score_mood
                + 0.20 * score_runtime
                + 0.15 * score_company
                + 0.05 * score_intensity
                + 0.15 * score_language
            )
        else:
            overall = (
                0.50 * score_mood
                + 0.20 * score_runtime
                + 0.15 * score_company
                + 0.10 * score_intensity
                + 0.05 * score_language
            )
    elif context.language and context.language.lower() != "any":
        overall = (
            0.25 * score_runtime
            + 0.25 * score_mood
            + 0.15 * score_company
            + 0.10 * score_intensity
            + 0.25 * score_language
        )
    else:
        overall = (
            0.30 * score_runtime
            + 0.30 * score_mood
            + 0.20 * score_company
            + 0.10 * score_intensity
            + 0.10 * score_language
        )
    return float(overall), sub_scores


def compute_bayesian_quality(vote_average: float, vote_count: int, m: float = 100.0, C: float = 6.5) -> float:
    """Bayesian smoothed rating normalized to [0.0, 1.0]."""
    v = float(vote_count)
    R = float(vote_average)
    smoothed = (v / (v + m)) * R + (m / (v + m)) * C
    return float(np.clip(smoothed / 10.0, 0.0, 1.0))


def compute_recent_behavior_score(
    movie_vector: np.ndarray,
    recent_liked_vectors: List[np.ndarray],
    fallback_similarity: float,
) -> float:
    """Compute maximum cosine similarity to user's recently liked items."""
    if not recent_liked_vectors:
        return fallback_similarity
    sims = [float(np.dot(movie_vector, rv)) for rv in recent_liked_vectors]
    max_sim = max(sims)
    return float(np.clip((max_sim + 1.0) / 2.0, 0.0, 1.0))


def mmr_diversity_rerank(
    candidate_indices: List[int],
    relevance_scores: List[float],
    feature_matrix: np.ndarray,
    top_k: int = 20,
    lambda_param: float = 0.7,
) -> List[int]:
    """
    Maximal Marginal Relevance (MMR) re-ranking.
    Balances individual recommendation quality with catalog diversity.
    """
    if len(candidate_indices) <= top_k:
        return candidate_indices

    selected_indices: List[int] = []
    candidate_pool = list(zip(candidate_indices, relevance_scores))

    # Pick the top relevance item first
    candidate_pool.sort(key=lambda x: x[1], reverse=True)
    selected_indices.append(candidate_pool.pop(0)[0])

    while len(selected_indices) < top_k and candidate_pool:
        best_idx = -1
        best_mmr = -float("inf")
        selected_vectors = feature_matrix[selected_indices]

        for i, (cand_idx, rel_score) in enumerate(candidate_pool):
            cand_vec = feature_matrix[cand_idx]
            # Max similarity with already selected items
            max_sim = float(np.max(np.dot(selected_vectors, cand_vec)))
            mmr_score = lambda_param * rel_score - (1.0 - lambda_param) * max_sim

            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_idx = i

        selected_indices.append(candidate_pool.pop(best_idx)[0])

    return selected_indices


class CineMatchRecommender:
    """Main CineMatch recommendation ranking engine."""

    def __init__(
        self,
        features: ProcessedFeatures,
        collaborative_model: Optional[SimpleCollaborativeModel] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.features = features
        self.collab_model = collaborative_model or SimpleCollaborativeModel()
        self.config = config or load_recommender_config()

    def get_recommendations(
        self,
        profile_vector: np.ndarray,
        interactions: Optional[List[UserInteraction]] = None,
        context: Optional[SessionContext] = None,
        top_k: int = 10,
        candidate_pool_size: int = 200,
    ) -> List[RecommendationItem]:
        """Generate final multi-objective ranked recommendations with MMR diversity."""
        df = self.features.movies_df
        N = len(df)
        if N == 0:
            return []

        # Determine unseen_only preference (default True)
        unseen_only = context.unseen_only if (context and context.unseen_only is not None) else True

        # 1. Categorize interactions: watched/liked vs disliked
        excluded_ids: Set[int] = set()
        user_watched_ids: Set[int] = set()
        user_disliked_ids: Set[int] = set()
        recent_liked_ids: List[int] = []
        recent_liked_vectors: List[np.ndarray] = []

        if interactions:
            for item in sorted(interactions, key=lambda x: x.timestamp or 0.0, reverse=True):
                itype = item.interaction_type.lower()
                if itype == "dislike" or (item.rating and item.rating <= 2.0):
                    user_disliked_ids.add(item.movie_id)
                elif itype in ["watched", "like"] or (item.rating and item.rating >= 3.0):
                    user_watched_ids.add(item.movie_id)
                    if itype == "like" or (item.rating and item.rating >= 4.0):
                        if item.movie_id not in recent_liked_ids:
                            recent_liked_ids.append(item.movie_id)
                            vec = self.features.get_movie_vector(item.movie_id)
                            if vec is not None and len(recent_liked_vectors) < 4:
                                recent_liked_vectors.append(vec)

        # Disliked titles are always excluded
        excluded_ids.update(user_disliked_ids)

        # When unseen_only is ON, never show movies the user already marked as watched, liked, rated, or disliked
        if unseen_only:
            excluded_ids.update(user_watched_ids)

        # 2. Context mature filter for family company
        if context and context.company in ["family", "kids"]:
            for idx, row in df.iterrows():
                if (
                    row.get("intensity") == "intense"
                    or "dark" in row.get("moods", [])
                    or any(g in ["Horror", "Crime", "War"] for g in row.get("genres_list", []))
                ):
                    excluded_ids.add(int(row["id"]))

        # 3. Base profile similarity for candidate pool pre-selection
        all_profile_sims = np.dot(self.features.feature_matrix, profile_vector)
        # Normalize [-1, 1] to [0, 1]
        all_profile_sims = np.clip((all_profile_sims + 1.0) / 2.0, 0.0, 1.0)

        # Candidate indices excluding filtered items
        valid_indices = [
            i for i, row in df.iterrows()
            if int(row["id"]) not in excluded_ids
        ]

        if not valid_indices:
            # If user explicitly requested unseen movies, return empty so frontend shows friendly empty state
            if unseen_only:
                return []
            valid_indices = list(range(N))

        # Log mood and apply strong mood filtering first (relaxing threshold step by step)
        target_mood = context.mood.lower().strip() if (context and context.mood) else None
        active_mood_thresh = 0.0
        logger.info("Recommender engine processing request with context mood: '%s'", target_mood)

        if target_mood:
            relaxation_thresholds = [0.60, 0.45, 0.35, 0.25, 0.15, 0.0]
            for thresh in relaxation_thresholds:
                matching = [
                    i for i in valid_indices
                    if df.iloc[i].get("mood_scores", {}).get(target_mood, 0.0) >= thresh
                ]
                if len(matching) >= 20 or thresh == 0.0:
                    valid_indices = matching
                    active_mood_thresh = thresh
                    break
            logger.info("Mood filter for '%s': selected threshold %.2f yielding %d candidates", target_mood, active_mood_thresh, len(valid_indices))

        # Sort candidate indices by profile similarity
        valid_indices.sort(key=lambda idx: all_profile_sims[idx], reverse=True)

        # Prioritize rewatch titles if unseen_only is False so they get evaluated in candidate pool
        if not unseen_only and user_watched_ids:
            watched_indices = [i for i in valid_indices if int(df.iloc[i]["id"]) in user_watched_ids]
            other_indices = [i for i in valid_indices if int(df.iloc[i]["id"]) not in user_watched_ids]
            valid_indices = watched_indices + other_indices

        # If a specific language is requested, ensure all valid matching titles are included at the top of candidate pool
        if context and context.language and context.language.lower() != "any":
            target_lang = context.language.lower().strip()
            matching_lang_indices = [
                i for i in valid_indices
                if str(df.iloc[i].get("original_language", "")).lower() == target_lang
            ]
            other_indices = [i for i in valid_indices if i not in matching_lang_indices]
            candidate_indices = (matching_lang_indices + other_indices)[:candidate_pool_size]
        else:
            candidate_indices = valid_indices[:candidate_pool_size]

        # 4. Resolve weights
        w_cfg = self.config.get("ranking", {}).get("weights", {})
        w_profile = float(w_cfg.get("profile_similarity", 0.30))
        w_recent = float(w_cfg.get("recent_behavior", 0.15))
        w_context = float(w_cfg.get("context_match", 0.35))
        w_collab = float(w_cfg.get("collaborative_score", 0.10))
        w_quality = float(w_cfg.get("quality_prior", 0.10))

        # Deactivate collaborative filtering if model has insufficient data
        if not self.collab_model.is_active:
            w_collab = 0.0

        total_weight = w_profile + w_recent + w_context + w_collab + w_quality
        if total_weight > 0:
            w_profile /= total_weight
            w_recent /= total_weight
            w_context /= total_weight
            w_collab /= total_weight
            w_quality /= total_weight

        # 5. Compute components and final score for candidates
        candidate_records = []

        for idx in candidate_indices:
            row = df.iloc[idx]
            mid = int(row["id"])
            m_vec = self.features.feature_matrix[idx]

            # Profile similarity
            s_prof = float(all_profile_sims[idx])

            # Recent behavior
            s_recent = compute_recent_behavior_score(
                movie_vector=m_vec,
                recent_liked_vectors=recent_liked_vectors,
                fallback_similarity=s_prof,
            )

            # Context match
            s_context, _ = compute_context_score(row, context)

            # Collaborative score
            s_collab = self.collab_model.score_candidate(mid, recent_liked_ids) if w_collab > 0 else 0.0

            # Quality prior
            s_quality = compute_bayesian_quality(
                vote_average=float(row.get("vote_average", 6.0)),
                vote_count=int(row.get("vote_count", 0)),
            )

            # Language boost when user requested specific language
            lang_boost = 0.0
            if context and context.language and context.language.lower() != "any":
                if str(row.get("original_language", "")).lower() == context.language.lower().strip():
                    lang_boost = 0.20

            # Rewatch boost when user chose 'Rewatch a favourite'
            rewatch_boost = 0.0
            if not unseen_only and mid in user_watched_ids:
                rewatch_boost = 0.35

            final_score = (
                w_profile * s_prof
                + w_recent * s_recent
                + w_context * s_context
                + w_collab * s_collab
                + w_quality * s_quality
                + lang_boost
                + rewatch_boost
            )
            final_score = float(np.clip(final_score, 0.0, 1.0))

            breakdown = {
                "profile_similarity": round(s_prof, 4),
                "recent_behavior": round(s_recent, 4),
                "context_match": round(s_context, 4),
                "collaborative_score": round(s_collab, 4),
                "quality_prior": round(s_quality, 4),
                "final_score": round(float(final_score), 4),
            }

            row_dict = row.to_dict()
            row_dict["is_watched"] = bool(mid in user_watched_ids)

            candidate_records.append((idx, final_score, breakdown, row_dict))

        # Enforce minimum mood score cutoff for top candidates if mood was specified
        if target_mood and active_mood_thresh > 0:
            mood_filtered = [
                c for c in candidate_records
                if c[3].get("mood_scores", {}).get(target_mood, 0.0) >= min(0.25, active_mood_thresh)
            ]
            if len(mood_filtered) >= min(top_k, 5):
                candidate_records = mood_filtered

        # 6. Apply MMR Diversity Re-ranking
        mmr_cfg = self.config.get("ranking", {}).get("mmr", {})
        use_mmr = mmr_cfg.get("enabled", True)
        lambda_param = float(mmr_cfg.get("lambda_param", 0.7))

        pool_indices = [c[0] for c in candidate_records]
        pool_scores = [c[1] for c in candidate_records]

        if use_mmr and len(pool_indices) > 1:
            selected_indices = mmr_diversity_rerank(
                candidate_indices=pool_indices,
                relevance_scores=pool_scores,
                feature_matrix=self.features.feature_matrix,
                top_k=min(top_k, len(pool_indices)),
                lambda_param=lambda_param,
            )
        else:
            selected_indices = pool_indices[:top_k]

        idx_to_record = {c[0]: c for c in candidate_records}

        results: List[RecommendationItem] = []
        for idx in selected_indices:
            _, score, breakdown, meta = idx_to_record[idx]
            results.append(
                RecommendationItem(
                    movie_id=int(meta["id"]),
                    title=str(meta.get("title", "")),
                    final_score=score,
                    score_breakdown=breakdown,
                    metadata=meta,
                )
            )

        return results
