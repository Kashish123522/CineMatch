import time
import numpy as np
import pytest

from backend.ml.features import load_and_clean_movies, build_features
from backend.ml.profile import (
    DEFAULT_HALF_LIFE_DAYS,
    UserInteraction,
    calculate_interaction_weight,
    create_initial_profile_vector,
    get_movie_dna_summary,
    update_profile_vector,
)


@pytest.fixture(scope="module")
def features():
    df = load_and_clean_movies()
    return build_features(df)


def test_create_initial_profile_vector(features):
    # Inception id: 27205
    profile = create_initial_profile_vector(
        features=features,
        liked_movie_ids=[27205],
        preferred_genres=["Action", "Science Fiction"],
        preferred_languages=["en"],
        preferred_moods=["thoughtful", "thrilling"],
    )

    assert profile.shape == (features.feature_dim,)
    norm = np.linalg.norm(profile)
    assert np.isclose(norm, 1.0, atol=1e-4)

    # Inception vector similarity should be high
    inc_vec = features.get_movie_vector(27205)
    similarity = np.dot(profile, inc_vec)
    assert similarity > 0.6


def test_recency_decay_calculation():
    now = time.time()
    day_seconds = 86400.0

    inter_fresh = UserInteraction(movie_id=1, interaction_type="like", timestamp=now)
    weight_fresh = calculate_interaction_weight(inter_fresh, reference_time=now, half_life_days=14.0)
    assert np.isclose(weight_fresh, 1.0)

    # Exactly 1 half-life ago (14 days) -> weight should be 0.5
    inter_14d = UserInteraction(movie_id=1, interaction_type="like", timestamp=now - (14 * day_seconds))
    weight_14d = calculate_interaction_weight(inter_14d, reference_time=now, half_life_days=14.0)
    assert np.isclose(weight_14d, 0.5, atol=1e-3)

    # 28 days ago (2 half-lives) -> weight should be 0.25
    inter_28d = UserInteraction(movie_id=1, interaction_type="like", timestamp=now - (28 * day_seconds))
    weight_28d = calculate_interaction_weight(inter_28d, reference_time=now, half_life_days=14.0)
    assert np.isclose(weight_28d, 0.25, atol=1e-3)

    # Dislike should have negative weight
    inter_dislike = UserInteraction(movie_id=1, interaction_type="dislike", timestamp=now)
    weight_dislike = calculate_interaction_weight(inter_dislike, reference_time=now, half_life_days=14.0)
    assert np.isclose(weight_dislike, -1.0)

    # Ratings scaling: 5 stars -> 1.0, 1 star -> -1.0, 3 stars -> 0.0
    r5 = calculate_interaction_weight(UserInteraction(movie_id=1, interaction_type="rating", rating=5.0, timestamp=now), now)
    r1 = calculate_interaction_weight(UserInteraction(movie_id=1, interaction_type="rating", rating=1.0, timestamp=now), now)
    r3 = calculate_interaction_weight(UserInteraction(movie_id=1, interaction_type="rating", rating=3.0, timestamp=now), now)
    assert np.isclose(r5, 1.0)
    assert np.isclose(r1, -1.0)
    assert np.isclose(r3, 0.0)


def test_dislike_pushes_vector_away(features):
    # Start with a neutral or Spirited Away seed
    spirited_away_id = 129
    pulp_fiction_id = 680

    initial_profile = create_initial_profile_vector(
        features=features,
        liked_movie_ids=[spirited_away_id],
        preferred_genres=["Animation"],
    )

    pulp_vec = features.get_movie_vector(pulp_fiction_id)
    sim_before = np.dot(initial_profile, pulp_vec)

    # User dislikes Pulp Fiction
    interactions = [
        UserInteraction(movie_id=pulp_fiction_id, interaction_type="dislike", timestamp=time.time())
    ]
    updated_profile = update_profile_vector(
        current_profile=initial_profile,
        interactions=interactions,
        features=features,
        learning_rate=0.5,
    )

    sim_after = np.dot(updated_profile, pulp_vec)
    # Disliking Pulp Fiction MUST push the vector away (lower similarity)
    assert sim_after < sim_before


def test_like_pulls_vector_closer(features):
    inception_id = 27205
    initial_profile = create_initial_profile_vector(
        features=features,
        preferred_genres=["Comedy"],  # Different genre
    )

    inc_vec = features.get_movie_vector(inception_id)
    sim_before = np.dot(initial_profile, inc_vec)

    # User likes Inception
    interactions = [
        UserInteraction(movie_id=inception_id, interaction_type="like", timestamp=time.time())
    ]
    updated_profile = update_profile_vector(
        current_profile=initial_profile,
        interactions=interactions,
        features=features,
        learning_rate=0.4,
    )

    sim_after = np.dot(updated_profile, inc_vec)
    assert sim_after > sim_before


def test_movie_dna_summary(features):
    profile = create_initial_profile_vector(
        features=features,
        liked_movie_ids=[27205],  # Inception
        preferred_genres=["Science Fiction", "Action"],
        preferred_moods=["thoughtful"],
    )

    summary = get_movie_dna_summary(profile, features)
    assert "top_genres" in summary
    assert "top_moods" in summary
    assert "top_languages" in summary
    assert "top_directors_actors" in summary
    assert "typical_runtime_minutes" in summary
    assert "typical_intensity" in summary
    assert "recent_trend" in summary

    # Verify Christopher Nolan or DiCaprio shows up in top talent
    assert any("Nolan" in talent or "DiCaprio" in talent for talent in summary["top_directors_actors"])

    # Test with recent interactions
    interactions = [
        UserInteraction(movie_id=27205, interaction_type="like", timestamp=time.time()),
        UserInteraction(movie_id=680, interaction_type="dislike", timestamp=time.time() - 3600),
    ]
    summary_with_trend = get_movie_dna_summary(profile, features, recent_interactions=interactions)
    assert "Inception" in summary_with_trend["recent_trend"]
