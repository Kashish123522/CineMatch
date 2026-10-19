"""
CineMatch - Explainability & Reason Chips Engine
Generates template-based natural language explanations and structured reason chips
grounded in the recommendation's score breakdown and session context.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from backend.ml.recommender import RecommendationItem, SessionContext


LANG_MAP: Dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "ja": "Japanese",
    "fr": "French",
    "es": "Spanish",
    "ko": "Korean",
    "de": "German",
    "it": "Italian",
    "zh": "Chinese",
    "cn": "Cantonese",
}


def generate_explanation(
    item: RecommendationItem,
    context: Optional[SessionContext] = None,
    recent_liked_titles: Optional[List[str]] = None,
    user_top_genres: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    """
    Generate natural-language explanation and 2-4 structured reason chips.
    Returns: (explanation_text, reason_chips)
    """
    meta = item.metadata
    scores = item.score_breakdown

    runtime = int(meta.get("runtime", 100))
    vote_avg = float(meta.get("vote_average", 6.0))
    genres = meta.get("genres_list", [])
    moods = meta.get("moods", [])
    director = str(meta.get("director", "")).strip()
    movie_lang = str(meta.get("original_language", "en")).lower()
    lang_display = LANG_MAP.get(movie_lang, movie_lang.upper())

    reason_chips: List[str] = []
    sentence_clauses: List[str] = []

    # 1. Anchored on recent liked movie or taste profile
    primary_anchor = None
    if recent_liked_titles and scores.get("recent_behavior", 0.0) >= 0.55:
        primary_anchor = recent_liked_titles[0]
        reason_chips.append(f"Because you liked {primary_anchor}")
        genre_name = genres[0] if genres else "cinematic"
        sentence_clauses.append(f"Because you liked {primary_anchor}, this shares similar {genre_name.lower()} elements")
    elif user_top_genres and any(g in user_top_genres for g in genres):
        matching_g = next(g for g in genres if g in user_top_genres)
        reason_chips.append(f"High {matching_g} synergy")
        mood_str = f" {moods[0]}" if moods else ""
        sentence_clauses.append(f"Strongly aligns with your affinity for{mood_str} {matching_g.lower()}")
    else:
        genre_str = f"{genres[0]} " if genres else ""
        sentence_clauses.append(f"A high-affinity {genre_str}recommendation for your taste profile")

    # 2. Context match (Language)
    if context and context.language and context.language.lower() != "any":
        target_lang = context.language.lower().strip()
        if movie_lang == target_lang:
            reason_chips.append(f"In {lang_display}")
            sentence_clauses.append(f"is in {lang_display}")
    elif movie_lang in ["hi", "ta", "te", "ja", "ko", "fr", "es", "de"]:
        reason_chips.append(f"In {lang_display}")

    # 3. Context match (Runtime)
    context_runtime_fits = False
    if context and context.time_available_minutes:
        limit = context.time_available_minutes
        if runtime <= limit:
            context_runtime_fits = True
            reason_chips.append(f"Fits your {limit}m window")
            sentence_clauses.append(f"fits right inside your {limit}-minute time limit")
        elif runtime <= limit + 15:
            reason_chips.append(f"Near {limit}m limit ({runtime}m)")

    # 4. Context match (Mood)
    if context and context.mood:
        cmood = context.mood.lower().strip()
        mood_scores = meta.get("mood_scores", {})
        if isinstance(mood_scores, dict) and cmood in mood_scores:
            m_score = float(mood_scores[cmood])
        else:
            m_score = 1.0 if cmood in [m.lower() for m in moods] else 0.0

        if m_score >= 0.45:
            reason_chips.append(f"Matches '{cmood}' mood")
            if not context_runtime_fits:
                sentence_clauses.append(f"delivers the {cmood} atmosphere you're looking for")

    # 5. Context match (Company)
    if context and context.company:
        comp = context.company.lower()
        if comp in ["date_night", "date"]:
            reason_chips.append("Great for Date Night")
        elif comp in ["family", "kids"]:
            reason_chips.append("Family Friendly")
        elif comp in ["friends"]:
            reason_chips.append("Fun with Friends")

    # 6. Quality & Director Chips
    if vote_avg >= 8.0:
        reason_chips.append(f"Critically acclaimed ({vote_avg}★)")
    elif director:
        reason_chips.append(f"Dir. by {director}")

    # 7. Novelty / Rewatch clauses & chips
    is_watched = bool(meta.get("is_watched", False))
    unseen_only = bool(context.unseen_only) if (context and context.unseen_only is not None) else True

    if is_watched:
        reason_chips.append("Watched")
        sentence_clauses.append("is a comforting rewatch of a favourite you loved")
    elif unseen_only:
        reason_chips.append("Fresh Discovery")
        sentence_clauses.append("is a fresh pick you haven't watched yet")

    # Build natural language explanation
    if len(sentence_clauses) == 1:
        if vote_avg >= 8.0:
            sentence = f"{sentence_clauses[0]} and holds a high {vote_avg}★ viewer rating."
        elif director:
            sentence = f"{sentence_clauses[0]}, directed by {director}."
        else:
            sentence = f"{sentence_clauses[0]}."
    elif len(sentence_clauses) == 2:
        sentence = f"{sentence_clauses[0]} and {sentence_clauses[1]}."
    elif len(sentence_clauses) == 3:
        sentence = f"{sentence_clauses[0]}, {sentence_clauses[1]}, and {sentence_clauses[2]}."
    else:
        sentence = f"{', '.join(sentence_clauses[:-1])}, and {sentence_clauses[-1]}."

    # Keep chips concise (2-5 chips)
    deduped_chips: List[str] = []
    for c in reason_chips:
        if c not in deduped_chips:
            deduped_chips.append(c)
    final_chips = deduped_chips[:5]

    return sentence, final_chips

