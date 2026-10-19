"""
CineMatch - Database Seeder Script
Creates synthetic users with distinct taste profiles, onboardings, and realistic interaction histories.
Ensures collaborative filtering thresholds are populated.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import time
from typing import List

# Ensure project root is in sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.database import SessionLocal, init_db
from backend.app.models import Interaction, User
from backend.ml.features import load_or_build_features
from backend.ml.profile import create_initial_profile_vector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_database():
    logger.info("Initializing database...")
    init_db()
    db = SessionLocal()
    features = load_or_build_features()
    df = features.movies_df

    logger.info("Loaded %d movies in catalog.", len(df))

    # Synthetic personas
    personas = [
        {
            "username": "alex_scifi",
            "liked_movie_ids": [27205, 157336],  # Inception, Interstellar
            "genres": ["Science Fiction", "Drama", "Adventure"],
            "languages": ["en"],
            "moods": ["thoughtful", "thrilling"],
            "interactions": [
                (27205, "like", None, 1),
                (157336, "rating", 5.0, 2),
                (155, "watched", None, 5),
                (680, "skip", None, 8),
                (129, "like", None, 12),
            ],
        },
        {
            "username": "sarah_action",
            "liked_movie_ids": [155, 27205],  # Dark Knight, Inception
            "genres": ["Action", "Crime", "Thriller"],
            "languages": ["en"],
            "moods": ["thrilling", "dark"],
            "interactions": [
                (155, "rating", 5.0, 1),
                (27205, "like", None, 3),
                (680, "like", None, 4),
                (157336, "watched", None, 7),
                (129, "skip", None, 10),
            ],
        },
        {
            "username": "elena_animation",
            "liked_movie_ids": [129],  # Spirited Away
            "genres": ["Animation", "Family", "Fantasy"],
            "languages": ["ja", "en"],
            "moods": ["feel-good", "inspiring"],
            "interactions": [
                (129, "rating", 5.0, 1),
                (157336, "like", None, 4),
                (27205, "watched", None, 6),
                (155, "dislike", None, 9),
                (680, "dislike", None, 11),
            ],
        },
        {
            "username": "marcus_cinephile",
            "liked_movie_ids": [680, 155],  # Pulp Fiction, Dark Knight
            "genres": ["Crime", "Thriller", "Drama"],
            "languages": ["en"],
            "moods": ["dark", "thrilling"],
            "interactions": [
                (680, "rating", 5.0, 1),
                (155, "like", None, 2),
                (27205, "like", None, 5),
                (157336, "rating", 4.0, 8),
                (129, "skip", None, 14),
            ],
        },
    ]

    now = time.time()
    day_sec = 86400.0

    total_interactions_added = 0

    for p in personas:
        user = db.query(User).filter(User.username == p["username"]).first()
        if not user:
            user = User(username=p["username"], onboarding_completed=True)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create Profile Vector
        vec = create_initial_profile_vector(
            features=features,
            liked_movie_ids=p["liked_movie_ids"],
            preferred_genres=p["genres"],
            preferred_languages=p["languages"],
            preferred_moods=p["moods"],
        )
        user.profile_vector = json.dumps([round(float(x), 5) for x in vec])
        user.onboarding_completed = True

        # Clear existing interactions to keep seed idempotent
        db.query(Interaction).filter(Interaction.user_id == user.id).delete()

        # Add interactions
        for mid, itype, rval, days_ago in p["interactions"]:
            ts = now - (days_ago * day_sec)
            inter = Interaction(
                user_id=user.id,
                movie_id=mid,
                interaction_type=itype,
                rating=rval,
                timestamp=ts,
            )
            db.add(inter)
            total_interactions_added += 1

        db.commit()
        logger.info("Seeded user '%s' (id=%d) with %d interactions.", user.username, user.id, len(p["interactions"]))

    db.close()
    logger.info("Successfully seeded database with %d interactions.", total_interactions_added)


if __name__ == "__main__":
    seed_database()
