import tempfile
from pathlib import Path
import numpy as np
import pytest

from backend.ml.features import (
    ALL_MOODS,
    build_features,
    derive_movie_labels,
    load_and_clean_movies,
    load_or_build_features,
)


def test_derive_movie_labels():
    # Feel good family movie
    moods, intensity, complexity = derive_movie_labels(
        genres=["Animation", "Family"],
        keywords=["magic", "friendship"],
        runtime=90,
    )
    assert "feel-good" in moods
    assert intensity == "light"
    assert complexity == "easy"

    # Dark thriller
    moods, intensity, complexity = derive_movie_labels(
        genres=["Crime", "Thriller"],
        keywords=["murder", "violence"],
        runtime=110,
    )
    assert "dark" in moods
    assert "thrilling" in moods
    assert intensity == "intense"

    # Thoughtful Sci-Fi
    moods, intensity, complexity = derive_movie_labels(
        genres=["Science Fiction", "Drama"],
        keywords=["space exploration", "subconscious"],
        runtime=150,
    )
    assert "thoughtful" in moods
    assert complexity == "complex"


def test_load_and_clean_movies():
    df = load_and_clean_movies()
    assert len(df) >= 5
    assert "title" in df.columns
    assert "genres_list" in df.columns
    assert "cast_list" in df.columns
    assert "director" in df.columns
    assert "moods" in df.columns
    assert "intensity" in df.columns
    assert "complexity" in df.columns

    # Verify Inception
    inception = df[df["title"] == "Inception"].iloc[0]
    assert inception["director"] == "Christopher Nolan"
    assert "Action" in inception["genres_list"]
    assert "Leonardo DiCaprio" in inception["cast_list"]


def test_build_features_normalization():
    df = load_and_clean_movies()
    features = build_features(df)

    assert features.feature_matrix.shape[0] == len(df)
    assert features.feature_dim > 0
    assert "genres" in features.feature_slices
    assert "moods" in features.feature_slices

    # Verify L2 normalization
    norms = np.linalg.norm(features.feature_matrix, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)

    # Check movie vector lookup
    vec = features.get_movie_vector(27205)  # Inception id
    assert vec is not None
    assert len(vec) == features.feature_dim


def test_caching_mechanism(tmp_path):
    cache_file = tmp_path / "test_cache.pkl"
    assert not cache_file.exists()

    f1 = load_or_build_features(cache_path=cache_file)
    assert cache_file.exists()

    # Load again (should load from cache)
    f2 = load_or_build_features(cache_path=cache_file)
    assert f1.feature_matrix.shape == f2.feature_matrix.shape
    assert np.allclose(f1.feature_matrix, f2.feature_matrix)
