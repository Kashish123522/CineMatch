"""
CineMatch - FastAPI Application Server
Provides RESTful endpoints for user onboarding, taste profiles (Movie DNA),
situational session recommendations, interaction feedback, and movie details.
"""

from contextlib import asynccontextmanager
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from sqlalchemy.orm import Session

from backend.app.database import get_db, init_db
from backend.app.models import Interaction, User, UserSession
from backend.app.poster import get_gradient_placeholder, resolve_poster_url
from backend.app.schemas import (
    ContextRequest,
    FeedbackRequest,
    FeedbackResponse,
    InteractionHistoryItem,
    MovieDetailResponse,
    MovieDNASummary,
    OnboardingCompleteRequest,
    OnboardingMovieItem,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationResponseItem,
    UserCreate,
    UserResponse,
)
from backend.ml.explain import generate_explanation
from backend.ml.features import ProcessedFeatures, load_or_build_features
from backend.ml.profile import (
    UserInteraction,
    create_initial_profile_vector,
    get_movie_dna_summary,
    update_profile_vector,
)
from backend.ml.recommender import (
    CineMatchRecommender,
    SessionContext,
    SimpleCollaborativeModel,
)

logger = logging.getLogger(__name__)

# Global ML singletons
ml_features: Optional[ProcessedFeatures] = None
recommender: Optional[CineMatchRecommender] = None
collab_model: Optional[SimpleCollaborativeModel] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global ml_features, recommender, collab_model
    init_db()
    ml_features = load_or_build_features()
    collab_model = SimpleCollaborativeModel(min_system_interactions=20)
    
    # Fit real collaborative filtering model from MovieLens if available
    ml_ratings_path = Path(__file__).resolve().parent.parent / "data" / "movielens" / "ratings.csv"
    ml_links_path = Path(__file__).resolve().parent.parent / "data" / "movielens" / "links.csv"
    if ml_ratings_path.exists() and ml_links_path.exists():
        valid_ids = set(ml_features.movies_df["id"])
        num_pos = collab_model.fit_from_movielens(ml_ratings_path, ml_links_path, valid_ids)
        logger.info("Fitted collaborative model with %d MovieLens ratings (is_active=%s)", num_pos, collab_model.is_active)
    else:
        logger.info("MovieLens ratings not found. Collaborative model remains dormant.")

    recommender = CineMatchRecommender(features=ml_features, collaborative_model=collab_model)
    logger.info("CineMatch ML models and database initialized.")
    yield


app = FastAPI(
    title="CineMatch API",
    description="Real-Time Context-Aware Movie Recommendation Engine",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_active_features() -> ProcessedFeatures:
    global ml_features
    if ml_features is None:
        ml_features = load_or_build_features()
    return ml_features


def _get_active_recommender() -> CineMatchRecommender:
    global recommender, ml_features, collab_model
    if recommender is None:
        feats = _get_active_features()
        if collab_model is None:
            collab_model = SimpleCollaborativeModel(min_system_interactions=20)
            ml_ratings_path = Path(__file__).resolve().parent.parent / "data" / "movielens" / "ratings.csv"
            ml_links_path = Path(__file__).resolve().parent.parent / "data" / "movielens" / "links.csv"
            if ml_ratings_path.exists() and ml_links_path.exists():
                valid_ids = set(feats.movies_df["id"])
                collab_model.fit_from_movielens(ml_ratings_path, ml_links_path, valid_ids)
        recommender = CineMatchRecommender(features=feats, collaborative_model=collab_model)
    return recommender


def _parse_profile_vector(vector_str: Optional[str]) -> Optional[np.ndarray]:
    """Parse JSON vector string into numpy float array."""
    if not vector_str:
        return None
    try:
        data = json.loads(vector_str)
        return np.array(data, dtype=np.float32)
    except Exception:
        return None


def _serialize_profile_vector(vec: np.ndarray) -> str:
    """Serialize numpy float array into JSON string."""
    return json.dumps([round(float(x), 5) for x in vec])


# ==============================================================================
# Endpoints
# ==============================================================================


@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(username=payload.username.strip(), onboarding_completed=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/api/onboarding/movies", response_model=List[OnboardingMovieItem])
def get_onboarding_movies(limit: int = 15, offset: int = 0, exclude_ids: Optional[str] = None):
    """
    Get a diverse set of anchor movies for onboarding across genres and moods.
    Supports offset and exclude_ids to allow refreshing poster sets.
    """
    features = _get_active_features()
    df = features.movies_df
    if df.empty:
        return []

    excluded_set = set()
    if exclude_ids:
        for x in exclude_ids.split(","):
            try:
                excluded_set.add(int(x.strip()))
            except ValueError:
                pass

    top_voted = df.sort_values(by=["vote_count", "vote_average"], ascending=[False, False])
    available = top_voted[~top_voted["id"].isin(excluded_set)] if excluded_set else top_voted
    if available.empty and not top_voted.empty:
        available = top_voted

    n_avail = len(available)
    start_idx = offset % n_avail if n_avail > 0 else 0
    if n_avail > 0:
        ordered_indices = list(range(start_idx, n_avail)) + list(range(0, start_idx))
        available = available.iloc[ordered_indices]

    diverse_selection = []
    seen_ids = set()

    for _, row in available.iterrows():
        mid = int(row["id"])
        if mid not in seen_ids:
            seen_ids.add(mid)
            diverse_selection.append(
                OnboardingMovieItem(
                    id=mid,
                    title=str(row["title"]),
                    year=int(row.get("year", 2000)),
                    genres=list(row.get("genres_list", [])),
                    moods=list(row.get("moods", [])),
                    runtime=int(row.get("runtime", 100)),
                    vote_average=float(row.get("vote_average", 6.0)),
                    poster_url=resolve_poster_url(mid, row.get("homepage")),
                    gradient=get_gradient_placeholder(mid, str(row["title"])),
                )
            )
        if len(diverse_selection) >= limit:
            break

    return diverse_selection


@app.post("/api/onboarding/complete", response_model=UserResponse)
def complete_onboarding(payload: OnboardingCompleteRequest, db: Session = Depends(get_db)):
    """
    Complete Spotify-style onboarding: construct initial Movie DNA vector and save liked seed movies.
    """
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    features = _get_active_features()

    # Build initial Movie DNA vector
    dna_vec = create_initial_profile_vector(
        features=features,
        liked_movie_ids=payload.liked_movie_ids,
        preferred_genres=payload.preferred_genres,
        preferred_languages=payload.preferred_languages,
        preferred_moods=payload.preferred_moods,
    )

    user.profile_vector = _serialize_profile_vector(dna_vec)
    user.onboarding_completed = True

    # Persist liked seed movies as initial interactions
    now = time.time()
    for mid in payload.liked_movie_ids:
        # Check if already exists
        exists = (
            db.query(Interaction)
            .filter(Interaction.user_id == user.id, Interaction.movie_id == mid)
            .first()
        )
        if not exists:
            db.add(
                Interaction(
                    user_id=user.id,
                    movie_id=mid,
                    interaction_type="like",
                    timestamp=now,
                )
            )

    db.commit()
    db.refresh(user)
    return user


@app.get("/api/users/{user_id}/dna", response_model=MovieDNASummary)
def get_user_dna(user_id: int, db: Session = Depends(get_db)):
    """Retrieve human-readable Movie DNA taste breakdown for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    features = _get_active_features()
    vec = _parse_profile_vector(user.profile_vector)
    if vec is None:
        # Generate default vector if not yet onboarded
        vec = create_initial_profile_vector(features=features)

    # Fetch recent interactions
    db_interactions = (
        db.query(Interaction)
        .filter(Interaction.user_id == user.id)
        .order_by(Interaction.timestamp.desc())
        .limit(20)
        .all()
    )
    interactions = [
        UserInteraction(
            movie_id=i.movie_id,
            interaction_type=i.interaction_type,
            rating=i.rating,
            timestamp=i.timestamp,
        )
        for i in db_interactions
    ]

    summary = get_movie_dna_summary(
        profile_vector=vec,
        features=features,
        recent_interactions=interactions,
    )

    return MovieDNASummary(
        user_id=user.id,
        top_genres=summary["top_genres"],
        top_moods=summary["top_moods"],
        top_languages=summary["top_languages"],
        top_directors_actors=summary["top_directors_actors"],
        typical_runtime_minutes=summary["typical_runtime_minutes"],
        typical_intensity=summary["typical_intensity"],
        recent_trend=summary["recent_trend"],
    )


@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(payload: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Generate ranked recommendations tailored for THIS user RIGHT NOW.
    Combines profile similarity, situational context, recency decay, and MMR diversity.
    """
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    incoming_mood = payload.context.mood if payload.context else None
    logger.info("POST /api/recommendations received for user_id=%s with context mood: '%s'", payload.user_id, incoming_mood)

    features = _get_active_features()
    rec_engine = _get_active_recommender()

    vec = _parse_profile_vector(user.profile_vector)
    if vec is None:
        vec = create_initial_profile_vector(features=features)

    # Fetch user interactions
    db_interactions = (
        db.query(Interaction)
        .filter(Interaction.user_id == user.id)
        .order_by(Interaction.timestamp.desc())
        .all()
    )
    interactions = [
        UserInteraction(
            movie_id=i.movie_id,
            interaction_type=i.interaction_type,
            rating=i.rating,
            timestamp=i.timestamp,
        )
        for i in db_interactions
    ]

    # Convert session context & record session in DB
    session_ctx = None
    if payload.context:
        c = payload.context
        session_ctx = SessionContext(
            time_available_minutes=c.time_available_minutes,
            mood=c.mood,
            company=c.company,
            intensity=c.intensity,
            complexity=c.complexity,
            language=c.language,
            unseen_only=True if c.unseen_only is None else c.unseen_only,
        )
        db.add(
            UserSession(
                user_id=user.id,
                time_available_minutes=c.time_available_minutes,
                mood=c.mood,
                company=c.company,
                intensity=c.intensity,
                complexity=c.complexity,
                language=c.language,
                unseen_only=True if c.unseen_only is None else c.unseen_only,
            )
        )
        db.commit()

    # Generate ranked recommendations
    ranked_items = rec_engine.get_recommendations(
        profile_vector=vec,
        interactions=interactions,
        context=session_ctx,
        top_k=payload.limit,
    )

    # Fetch recently liked titles for anchor explanations
    liked_ids = [
        i.movie_id for i in interactions
        if i.interaction_type in ["like", "watched"] or (i.rating and i.rating >= 4.0)
    ]
    recent_liked_titles = []
    for lid in liked_ids[:3]:
        r = features.movies_df[features.movies_df["id"] == lid]
        if not r.empty:
            recent_liked_titles.append(str(r["title"].values[0]))

    # Top user genres from profile
    summary = get_movie_dna_summary(profile_vector=vec, features=features)
    top_user_genres = [g["genre"] for g in summary.get("top_genres", [])]

    # Format response items with explanations and reason chips
    formatted_recs: List[RecommendationResponseItem] = []
    for item in ranked_items:
        meta = item.metadata
        mid = item.movie_id
        title = item.title

        explanation, chips = generate_explanation(
            item=item,
            context=session_ctx,
            recent_liked_titles=recent_liked_titles,
            user_top_genres=top_user_genres,
        )

        formatted_recs.append(
            RecommendationResponseItem(
                movie_id=mid,
                title=title,
                year=int(meta.get("year", 2000)),
                runtime=int(meta.get("runtime", 100)),
                genres=list(meta.get("genres_list", [])),
                moods=list(meta.get("moods", [])),
                intensity=str(meta.get("intensity", "medium")),
                complexity=str(meta.get("complexity", "moderate")),
                vote_average=float(meta.get("vote_average", 6.0)),
                poster_url=resolve_poster_url(mid, meta.get("homepage")),
                gradient=get_gradient_placeholder(mid, title),
                final_score=round(item.final_score, 4),
                score_breakdown=item.score_breakdown,
                explanation=explanation,
                reason_chips=chips,
                is_watched=bool(meta.get("is_watched", False)),
            )
        )

    return RecommendationResponse(
        user_id=user.id,
        count=len(formatted_recs),
        recommendations=formatted_recs,
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Record user interaction (like, dislike, rating, watched, skip)
    and adapt user profile vector incrementally with exponential recency decay.
    """
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    features = _get_active_features()
    movie_exists = not features.movies_df[features.movies_df["id"] == payload.movie_id].empty
    if not movie_exists:
        raise HTTPException(status_code=404, detail="Movie not found in catalog")

    now = time.time()
    interaction = Interaction(
        user_id=user.id,
        movie_id=payload.movie_id,
        interaction_type=payload.interaction_type.lower(),
        rating=payload.rating,
        timestamp=now,
    )
    db.add(interaction)

    # Adapt user profile vector dynamically
    cur_vec = _parse_profile_vector(user.profile_vector)
    if cur_vec is None:
        cur_vec = create_initial_profile_vector(features=features)

    u_inter = UserInteraction(
        movie_id=payload.movie_id,
        interaction_type=payload.interaction_type.lower(),
        rating=payload.rating,
        timestamp=now,
    )

    updated_vec = update_profile_vector(
        current_profile=cur_vec,
        interactions=[u_inter],
        features=features,
    )
    user.profile_vector = _serialize_profile_vector(updated_vec)

    db.commit()

    return FeedbackResponse(
        status="success",
        user_id=user.id,
        movie_id=payload.movie_id,
        interaction_type=payload.interaction_type,
        message=f"Interaction '{payload.interaction_type}' recorded and Movie DNA updated.",
    )


@app.get("/api/movies/{movie_id}", response_model=MovieDetailResponse)
def get_movie_detail(movie_id: int):
    """Retrieve full metadata for a single movie."""
    features = _get_active_features()
    df = features.movies_df
    row = df[df["id"] == movie_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Movie not found")

    r = row.iloc[0]
    title = str(r["title"])

    return MovieDetailResponse(
        id=int(r["id"]),
        title=title,
        year=int(r.get("year", 2000)),
        runtime=int(r.get("runtime", 100)),
        overview=str(r.get("overview", "")),
        genres=list(r.get("genres_list", [])),
        keywords=list(r.get("keywords_list", [])),
        cast=list(r.get("cast_list", [])),
        director=str(r.get("director", "")),
        original_language=str(r.get("original_language", "en")),
        vote_average=float(r.get("vote_average", 6.0)),
        vote_count=int(r.get("vote_count", 0)),
        popularity=float(r.get("popularity", 1.0)),
        moods=list(r.get("moods", [])),
        intensity=str(r.get("intensity", "medium")),
        complexity=str(r.get("complexity", "moderate")),
        poster_url=resolve_poster_url(movie_id, r.get("homepage")),
        gradient=get_gradient_placeholder(movie_id, title),
    )


@app.get("/api/users/{user_id}/history", response_model=List[InteractionHistoryItem])
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    """Retrieve chronologically ordered interaction history for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    features = _get_active_features()
    df = features.movies_df

    interactions = (
        db.query(Interaction)
        .filter(Interaction.user_id == user.id)
        .order_by(Interaction.timestamp.desc())
        .all()
    )

    history: List[InteractionHistoryItem] = []
    for i in interactions:
        match = df[df["id"] == i.movie_id]
        title = match["title"].values[0] if not match.empty else f"Movie #{i.movie_id}"
        history.append(
            InteractionHistoryItem(
                id=i.id,
                movie_id=i.movie_id,
                movie_title=str(title),
                interaction_type=i.interaction_type,
                rating=i.rating,
                timestamp=i.timestamp,
                created_at=i.created_at,
            )
        )

    return history
