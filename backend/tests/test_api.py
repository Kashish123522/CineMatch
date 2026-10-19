"""
CineMatch - API Endpoint Test Suite
Tests all 8 REST endpoints using FastAPI TestClient with SQLite test database.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.scripts.seed import seed_database

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database and seed data are ready for tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def test_create_user_and_duplicate_check():
    # Create new user
    res = client.post("/api/users", json={"username": "test_user_unique_1"})
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "test_user_unique_1"
    assert data["onboarding_completed"] is False
    assert "id" in data

    # Duplicate check
    res_dup = client.post("/api/users", json={"username": "test_user_unique_1"})
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]


def test_get_onboarding_movies():
    res = client.get("/api/onboarding/movies?limit=5")
    assert res.status_code == 200
    movies = res.json()
    assert len(movies) >= 1
    m = movies[0]
    assert "id" in m
    assert "title" in m
    assert "year" in m
    assert "genres" in m
    assert "moods" in m
    assert "gradient" in m


def test_complete_onboarding():
    # Register user
    user_res = client.post("/api/users", json={"username": "onboarding_tester"})
    uid = user_res.json()["id"]

    # Complete onboarding
    payload = {
        "user_id": uid,
        "liked_movie_ids": [27205],  # Inception
        "preferred_genres": ["Science Fiction", "Action"],
        "preferred_languages": ["en"],
        "preferred_moods": ["thoughtful"],
    }
    res = client.post("/api/onboarding/complete", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == uid
    assert data["onboarding_completed"] is True


def test_get_user_dna():
    # User 1 is alex_scifi (from seed)
    res = client.get("/api/users/1/dna")
    assert res.status_code == 200
    dna = res.json()
    assert dna["user_id"] == 1
    assert "top_genres" in dna
    assert "top_moods" in dna
    assert "top_languages" in dna
    assert "top_directors_actors" in dna
    assert "typical_runtime_minutes" in dna
    assert "typical_intensity" in dna
    assert "recent_trend" in dna


def test_get_recommendations_with_context():
    # User 1 (alex_scifi) requests recommendations with 150m limit and thoughtful mood
    payload = {
        "user_id": 1,
        "context": {
            "time_available_minutes": 150,
            "mood": "thoughtful",
            "company": "solo",
            "intensity": "intense",
            "language": "en",
        },
        "limit": 5,
    }
    res = client.post("/api/recommendations", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == 1
    assert "recommendations" in data
    recs = data["recommendations"]
    assert len(recs) > 0

    top_rec = recs[0]
    assert "movie_id" in top_rec
    assert "title" in top_rec
    assert "final_score" in top_rec
    assert "score_breakdown" in top_rec
    assert "explanation" in top_rec
    assert "reason_chips" in top_rec
    assert isinstance(top_rec["reason_chips"], list)
    assert len(top_rec["reason_chips"]) > 0


def test_submit_feedback_and_history():
    # Create user
    user_res = client.post("/api/users", json={"username": "feedback_user"})
    uid = user_res.json()["id"]

    # Submit a like
    fb_res = client.post(
        "/api/feedback",
        json={
            "user_id": uid,
            "movie_id": 27205,
            "interaction_type": "like",
        },
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["status"] == "success"

    # Submit a rating
    fb_rating = client.post(
        "/api/feedback",
        json={
            "user_id": uid,
            "movie_id": 157336,
            "interaction_type": "rating",
            "rating": 5.0,
        },
    )
    assert fb_rating.status_code == 200

    # Retrieve history
    hist_res = client.get(f"/api/users/{uid}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 2
    movie_titles = [h["movie_title"] for h in history]
    assert "Inception" in movie_titles
    assert "Interstellar" in movie_titles


def test_get_movie_detail():
    # Inception
    res = client.get("/api/movies/27205")
    assert res.status_code == 200
    m = res.json()
    assert m["id"] == 27205
    assert m["title"] == "Inception"
    assert m["director"] == "Christopher Nolan"
    assert "Action" in m["genres"]
    assert "gradient" in m

    # Not found
    res_404 = client.get("/api/movies/999999999")
    assert res_404.status_code == 404
