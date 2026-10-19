"""
CineMatch - Pydantic Request & Response Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- User Schemas ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    onboarding_completed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Onboarding Schemas ---
class OnboardingMovieItem(BaseModel):
    id: int
    title: str
    year: int
    genres: List[str]
    moods: List[str]
    runtime: int
    vote_average: float
    poster_url: Optional[str] = None
    gradient: str


class OnboardingCompleteRequest(BaseModel):
    user_id: int
    liked_movie_ids: List[int] = Field(default_factory=list)
    preferred_genres: List[str] = Field(default_factory=list)
    preferred_languages: List[str] = Field(default_factory=list)
    preferred_moods: List[str] = Field(default_factory=list)


# --- Movie DNA Schemas ---
class GenreAffinity(BaseModel):
    genre: str
    affinity: float
    percentage: int


class MoodAffinity(BaseModel):
    mood: str
    affinity: float


class MovieDNASummary(BaseModel):
    user_id: int
    top_genres: List[GenreAffinity]
    top_moods: List[MoodAffinity]
    top_languages: List[str]
    top_directors_actors: List[str]
    typical_runtime_minutes: int
    typical_intensity: str
    recent_trend: str


# --- Session Context & Recommendations ---
class ContextRequest(BaseModel):
    time_available_minutes: Optional[int] = Field(None, ge=15, le=360)
    mood: Optional[str] = None
    company: Optional[str] = None
    intensity: Optional[str] = None
    complexity: Optional[str] = None
    language: Optional[str] = None
    unseen_only: Optional[bool] = True


class RecommendationRequest(BaseModel):
    user_id: int
    context: Optional[ContextRequest] = None
    limit: int = Field(default=10, ge=1, le=50)


class ScoreBreakdown(BaseModel):
    profile_similarity: float
    recent_behavior: float
    context_match: float
    collaborative_score: float
    quality_prior: float
    final_score: float


class RecommendationResponseItem(BaseModel):
    movie_id: int
    title: str
    year: int
    runtime: int
    genres: List[str]
    moods: List[str]
    intensity: str
    complexity: str
    vote_average: float
    poster_url: Optional[str] = None
    gradient: str
    final_score: float
    score_breakdown: ScoreBreakdown
    explanation: str
    reason_chips: List[str]
    is_watched: bool = False


class RecommendationResponse(BaseModel):
    user_id: int
    count: int
    recommendations: List[RecommendationResponseItem]


# --- Feedback & History Schemas ---
class FeedbackRequest(BaseModel):
    user_id: int
    movie_id: int
    interaction_type: str = Field(..., pattern="^(like|dislike|rating|watched|skip)$")
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)


class FeedbackResponse(BaseModel):
    status: str
    user_id: int
    movie_id: int
    interaction_type: str
    message: str


class InteractionHistoryItem(BaseModel):
    id: int
    movie_id: int
    movie_title: str
    interaction_type: str
    rating: Optional[float]
    timestamp: float
    created_at: datetime


class MovieDetailResponse(BaseModel):
    id: int
    title: str
    year: int
    runtime: int
    overview: str
    genres: List[str]
    keywords: List[str]
    cast: List[str]
    director: str
    original_language: str
    vote_average: float
    vote_count: int
    popularity: float
    moods: List[str]
    intensity: str
    complexity: str
    poster_url: Optional[str] = None
    gradient: str
