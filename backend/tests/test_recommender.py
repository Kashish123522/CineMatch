import time
import numpy as np
import pytest

from backend.ml.explain import generate_explanation
from backend.ml.features import build_features, load_and_clean_movies
from backend.ml.profile import UserInteraction, create_initial_profile_vector
from backend.ml.recommender import (
    CineMatchRecommender,
    RecommendationItem,
    SessionContext,
    SimpleCollaborativeModel,
    compute_context_score,
)


@pytest.fixture(scope="module")
def features():
    df = load_and_clean_movies()
    return build_features(df)


@pytest.fixture(scope="module")
def recommender(features):
    return CineMatchRecommender(features=features)


def test_context_runtime_fit(features):
    df = features.movies_df
    # Spirited Away is 125 min, Interstellar is 169 min
    spirited_row = df[df["title"] == "Spirited Away"].iloc[0]
    interstellar_row = df[df["title"] == "Interstellar"].iloc[0]

    ctx_short = SessionContext(time_available_minutes=130)
    score_spirited, subs_s = compute_context_score(spirited_row, ctx_short)
    score_interstellar, subs_i = compute_context_score(interstellar_row, ctx_short)

    assert subs_s["runtime"] == 1.0
    assert subs_i["runtime"] < 1.0
    assert score_spirited > score_interstellar


def test_context_family_filters_mature_content(features):
    df = features.movies_df
    dark_knight = df[df["title"] == "The Dark Knight"].iloc[0]
    spirited_away = df[df["title"] == "Spirited Away"].iloc[0]

    family_ctx = SessionContext(company="family")

    # Dark Knight has Crime/Thriller and intense rating -> filtered to 0.0
    score_dk, _ = compute_context_score(dark_knight, family_ctx)
    assert score_dk == 0.0

    # Spirited Away is Family/Animation -> highly rated
    score_sa, subs_sa = compute_context_score(spirited_away, family_ctx)
    assert score_sa > 0.7
    assert subs_sa["company"] == 1.0


def test_context_mood_and_language(features):
    df = features.movies_df
    inception = df[df["title"] == "Inception"].iloc[0]

    ctx_thoughtful = SessionContext(mood="thoughtful", language="en")
    score_match, subs_match = compute_context_score(inception, ctx_thoughtful)

    ctx_mismatch = SessionContext(mood="funny", language="ja")
    score_mismatch, subs_mismatch = compute_context_score(inception, ctx_mismatch)

    assert subs_match["mood"] > subs_mismatch["mood"]
    assert subs_match["language"] > subs_mismatch["language"]
    assert score_match > score_mismatch


def test_recommendations_exclude_watched_and_disliked(recommender, features):
    profile = create_initial_profile_vector(
        features=features,
        liked_movie_ids=[27205],  # Inception
    )

    # Inception is watched, Dark Knight is disliked
    interactions = [
        UserInteraction(movie_id=27205, interaction_type="watched"),
        UserInteraction(movie_id=155, interaction_type="dislike"),
    ]

    recs = recommender.get_recommendations(
        profile_vector=profile,
        interactions=interactions,
        top_k=5,
    )

    rec_ids = [r.movie_id for r in recs]
    assert 27205 not in rec_ids
    assert 155 not in rec_ids


def test_score_breakdowns_and_inactive_cf(recommender, features):
    profile = create_initial_profile_vector(features=features, preferred_genres=["Action"])
    recs = recommender.get_recommendations(profile_vector=profile, top_k=3)

    assert len(recs) > 0
    top_item = recs[0]
    breakdown = top_item.score_breakdown

    assert "profile_similarity" in breakdown
    assert "recent_behavior" in breakdown
    assert "context_match" in breakdown
    assert "collaborative_score" in breakdown
    assert "quality_prior" in breakdown
    assert "final_score" in breakdown

    # CF is inactive when no interaction data exists -> collaborative_score is 0.0
    assert breakdown["collaborative_score"] == 0.0
    assert 0.0 <= breakdown["final_score"] <= 1.0


def test_active_collaborative_filtering(features):
    # Fit collaborative model with >= 20 interactions
    cf = SimpleCollaborativeModel(min_system_interactions=5)
    interactions = [
        (1, 27205, 1.0), (1, 157336, 1.0),
        (2, 27205, 1.0), (2, 157336, 1.0),
        (3, 27205, 1.0), (3, 157336, 1.0),
        (4, 27205, 1.0), (4, 155, 1.0),
        (5, 155, 1.0), (5, 680, 1.0),
    ]
    cf.fit(interactions)
    assert cf.is_active is True

    # User liked Inception (27205) -> Interstellar (157336) should have high collab score
    collab_score = cf.score_candidate(157336, user_liked_ids=[27205])
    assert collab_score > 0.5


def test_explain_natural_language_and_chips():
    item_meta = {
        "id": 157336,
        "title": "Interstellar",
        "runtime": 169,
        "vote_average": 8.1,
        "genres_list": ["Adventure", "Drama", "Science Fiction"],
        "moods": ["thoughtful"],
        "director": "Christopher Nolan",
    }
    score_breakdown = {
        "profile_similarity": 0.85,
        "recent_behavior": 0.80,
        "context_match": 0.90,
        "collaborative_score": 0.0,
        "quality_prior": 0.82,
        "final_score": 0.84,
    }
    item = RecommendationItem(
        movie_id=157336,
        title="Interstellar",
        final_score=0.84,
        score_breakdown=score_breakdown,
        metadata=item_meta,
    )

    ctx = SessionContext(time_available_minutes=180, mood="thoughtful", company="solo")
    sentence, chips = generate_explanation(
        item=item,
        context=ctx,
        recent_liked_titles=["Inception"],
        user_top_genres=["Science Fiction"],
    )

    assert "Inception" in sentence
    assert "180-minute" in sentence
    assert any("Because you liked Inception" in c for c in chips)
    assert any("Fits your 180m window" in c for c in chips)
    assert any("Matches 'thoughtful' mood" in c for c in chips)
    assert any("Critically acclaimed" in c for c in chips)


def test_indian_languages_recommendation_and_fallback(recommender, features):
    profile = create_initial_profile_vector(features=features, preferred_genres=["Drama", "Action"])

    # Test Hindi
    ctx_hi = SessionContext(language="hi")
    recs_hi = recommender.get_recommendations(profile_vector=profile, context=ctx_hi, top_k=6)
    assert len(recs_hi) > 0, "Recommendations must never be empty for Hindi"
    hi_movies = [r for r in recs_hi if r.metadata.get("original_language") == "hi"]
    total_hi = len(features.movies_df[features.movies_df["original_language"] == "hi"])
    assert len(hi_movies) == min(6, total_hi), "All available Hindi titles up to top_k should be retrieved"
    assert len(recs_hi) == 6, "Recommender should gracefully backfill remaining slots"

    # Test Tamil
    ctx_ta = SessionContext(language="ta")
    recs_ta = recommender.get_recommendations(profile_vector=profile, context=ctx_ta, top_k=5)
    assert len(recs_ta) > 0, "Recommendations must never be empty for Tamil"
    ta_movies = [r for r in recs_ta if r.metadata.get("original_language") == "ta"]
    total_ta = len(features.movies_df[features.movies_df["original_language"] == "ta"])
    assert len(ta_movies) == min(5, total_ta), "All available Tamil titles should be retrieved"
    assert len(recs_ta) == 5, "Recommender should backfill remaining slots"

    # Test Telugu
    ctx_te = SessionContext(language="te")
    recs_te = recommender.get_recommendations(profile_vector=profile, context=ctx_te, top_k=5)
    assert len(recs_te) > 0, "Recommendations must never be empty for Telugu"
    te_movies = [r for r in recs_te if r.metadata.get("original_language") == "te"]
    total_te = len(features.movies_df[features.movies_df["original_language"] == "te"])
    assert len(te_movies) == min(5, total_te), "All available Telugu titles should be retrieved"
    assert len(recs_te) == 5, "Recommender should backfill remaining slots"


def test_indian_languages_explanation():
    # 3 Idiots (Hindi)
    item_3i = RecommendationItem(
        movie_id=20453,
        title="3 Idiots",
        final_score=0.92,
        score_breakdown={"recent_behavior": 0.0, "context_match": 0.95, "profile_similarity": 0.90},
        metadata={"id": 20453, "title": "3 Idiots", "original_language": "hi", "genres_list": ["Comedy", "Drama"], "runtime": 170, "vote_average": 8.0},
    )
    sentence_hi, chips_hi = generate_explanation(item=item_3i, context=SessionContext(language="hi"))
    assert "in Hindi" in sentence_hi
    assert "In Hindi" in chips_hi

    # Vikram (Tamil)
    item_vikram = RecommendationItem(
        movie_id=860159,
        title="Vikram",
        final_score=0.91,
        score_breakdown={"recent_behavior": 0.0, "context_match": 0.95, "profile_similarity": 0.90},
        metadata={"id": 860159, "title": "Vikram", "original_language": "ta", "genres_list": ["Action", "Thriller"], "runtime": 175, "vote_average": 8.3},
    )
    sentence_ta, chips_ta = generate_explanation(item=item_vikram, context=SessionContext(language="ta"))
    assert "in Tamil" in sentence_ta
    assert "In Tamil" in chips_ta

    # RRR (Telugu)
    item_rrr = RecommendationItem(
        movie_id=579974,
        title="RRR",
        final_score=0.95,
        score_breakdown={"recent_behavior": 0.0, "context_match": 0.95, "profile_similarity": 0.90},
        metadata={"id": 579974, "title": "RRR", "original_language": "te", "genres_list": ["Action", "Drama"], "runtime": 182, "vote_average": 8.1},
    )
    sentence_te, chips_te = generate_explanation(item=item_rrr, context=SessionContext(language="te"))
    assert "in Telugu" in sentence_te
    assert "In Telugu" in chips_te


def test_unseen_only_true_and_false(recommender, features):
    profile = create_initial_profile_vector(features=features, preferred_genres=["Action", "Drama"])

    # User watched Inception (27205) and liked Interstellar (157336)
    interactions = [
        UserInteraction(movie_id=27205, interaction_type="watched"),
        UserInteraction(movie_id=157336, interaction_type="like"),
    ]

    # When unseen_only = True: Watched & Liked movies MUST NOT appear
    ctx_unseen = SessionContext(unseen_only=True)
    recs_unseen = recommender.get_recommendations(profile_vector=profile, interactions=interactions, context=ctx_unseen, top_k=10)
    unseen_ids = [r.movie_id for r in recs_unseen]
    assert 27205 not in unseen_ids
    assert 157336 not in unseen_ids
    for r in recs_unseen:
        assert r.metadata.get("is_watched", False) is False

    # When unseen_only = False: Rewatch picks ARE allowed and tagged is_watched = True
    ctx_rewatch = SessionContext(unseen_only=False)
    recs_rewatch = recommender.get_recommendations(profile_vector=profile, interactions=interactions, context=ctx_rewatch, top_k=10)
    rewatch_ids = [r.movie_id for r in recs_rewatch]
    assert (27205 in rewatch_ids or 157336 in rewatch_ids), "Rewatch items should be included when unseen_only is False"

    watched_items = [r for r in recs_rewatch if r.movie_id in [27205, 157336]]
    for item in watched_items:
        assert item.metadata.get("is_watched") is True


def test_unseen_empty_case_returns_empty(recommender, features):
    profile = create_initial_profile_vector(features=features, preferred_genres=["Drama"])
    # Mark all movies in the catalog as watched
    all_ids = list(features.movies_df["id"])
    interactions = [UserInteraction(movie_id=mid, interaction_type="watched") for mid in all_ids]

    # When unseen_only is True, and all are watched -> return empty list so UI shows friendly message
    ctx_unseen = SessionContext(unseen_only=True)
    recs = recommender.get_recommendations(profile_vector=profile, interactions=interactions, context=ctx_unseen, top_k=5)
    assert len(recs) == 0


def test_unseen_and_rewatch_explanations():
    # Fresh unseen pick
    item_fresh = RecommendationItem(
        movie_id=27205,
        title="Inception",
        final_score=0.90,
        score_breakdown={"recent_behavior": 0.0, "context_match": 0.9, "profile_similarity": 0.9},
        metadata={"id": 27205, "title": "Inception", "original_language": "en", "genres_list": ["Action"], "is_watched": False},
    )
    sent_fresh, chips_fresh = generate_explanation(item=item_fresh, context=SessionContext(unseen_only=True))
    assert "fresh pick you haven't watched yet" in sent_fresh
    assert "Fresh Discovery" in chips_fresh

    # Rewatch pick
    item_rewatch = RecommendationItem(
        movie_id=157336,
        title="Interstellar",
        final_score=0.92,
        score_breakdown={"recent_behavior": 0.0, "context_match": 0.9, "profile_similarity": 0.9},
        metadata={"id": 157336, "title": "Interstellar", "original_language": "en", "genres_list": ["Adventure"], "is_watched": True},
    )
    sent_rewatch, chips_rewatch = generate_explanation(item=item_rewatch, context=SessionContext(unseen_only=False))
    assert "comforting rewatch" in sent_rewatch
    assert "Watched" in chips_rewatch


@pytest.mark.parametrize("mood", ["funny", "thrilling", "romantic", "thoughtful", "dark", "feel-good"])
def test_each_mood_top_10_has_high_average_mood_score(recommender, features, mood):
    profile = create_initial_profile_vector(features=features, preferred_genres=["Drama", "Comedy", "Action"])
    ctx = SessionContext(mood=mood)
    recs = recommender.get_recommendations(profile_vector=profile, context=ctx, top_k=10)
    assert len(recs) > 0

    mood_scores = [r.metadata.get("mood_scores", {}).get(mood, 0.0) for r in recs]
    avg_score = sum(mood_scores) / len(mood_scores)
    # Average mood score for top 10 must be high (>= 0.40)
    assert avg_score >= 0.40, f"Average {mood} score {avg_score:.2f} is below 0.40"
    for r in recs:
        score = r.metadata.get("mood_scores", {}).get(mood, 0.0)
        assert score >= 0.15, f"Movie {r.title} has low {mood} score: {score}"


def test_different_moods_produce_clearly_different_recommendations(recommender, features):
    profile = create_initial_profile_vector(features=features, preferred_genres=["Drama", "Comedy", "Action"])
    recs_funny = recommender.get_recommendations(profile_vector=profile, context=SessionContext(mood="funny"), top_k=10)
    recs_dark = recommender.get_recommendations(profile_vector=profile, context=SessionContext(mood="dark"), top_k=10)

    funny_ids = {r.movie_id for r in recs_funny}
    dark_ids = {r.movie_id for r in recs_dark}

    overlap = funny_ids & dark_ids
    # Overlap between funny and dark should be minimal (at most 2 out of 10)
    assert len(overlap) <= 2, f"Too much overlap between funny and dark: {overlap}"


