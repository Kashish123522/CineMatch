"""
CineMatch - SQLAlchemy Models
Defines users, movie interactions, and session contexts.
"""

from datetime import datetime, timezone
import time
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    onboarding_completed = Column(Boolean, default=False)
    # Stored as JSON string of float vector
    profile_vector = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    movie_id = Column(Integer, index=True, nullable=False)
    interaction_type = Column(String(50), nullable=False)  # 'like', 'dislike', 'rating', 'watched', 'skip'
    rating = Column(Float, nullable=True)
    timestamp = Column(Float, default=lambda: time.time())
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="interactions")


class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    time_available_minutes = Column(Integer, nullable=True)
    mood = Column(String(50), nullable=True)
    company = Column(String(50), nullable=True)
    intensity = Column(String(50), nullable=True)
    complexity = Column(String(50), nullable=True)
    language = Column(String(50), nullable=True)
    unseen_only = Column(Boolean, default=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="sessions")
