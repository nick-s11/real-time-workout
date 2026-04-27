"""Data models and Pydantic shapes used by the API.

This module contains the SQLModel table classes and request/response
schemas used by the routers. Timestamps are stored as ISO formatted
strings for simplicity in the frontend.
"""

from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """A persistent user record identified by a unique `name`."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=64, index=True, unique=True)


class WorkoutSession(SQLModel, table=True):
    """Represents a workout session that participants can join.

    The `session_id` is a short UUID string used by clients.
    """

    session_id: str = Field(primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    active: bool = True


class SessionParticipant(SQLModel, table=True):
    """Join table linking `User` records to `WorkoutSession`.

    A unique constraint prevents duplicate joins for the same user
    and session.
    """

    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_session_participant"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="workoutsession.session_id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    joined_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExerciseBase(SQLModel):
    """Shared exercise fields used for create/update and DB models."""

    type: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    sets: int = Field(default=0, ge=0, le=100)
    reps: int = Field(default=0, ge=0, le=1000)
    weight: float = Field(default=0.0, ge=0, le=5000)
    distance: float = Field(default=0.0, ge=0, le=1000)
    time: float = Field(default=0.0, ge=0, le=10000)
    user: str = Field(min_length=1, max_length=64)


class JoinWorkoutRequest(SQLModel):
    """Request body for joining a workout by name."""

    name: str = Field(min_length=1, max_length=64)


class ExerciseCreate(ExerciseBase):
    """Shape of data when creating a new exercise log."""

    type: Literal["lifting", "cardio"]


class ExerciseUpdate(SQLModel):
    """Fields that can be updated; all optional."""

    type: Optional[Literal["lifting", "cardio"]] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    sets: Optional[int] = Field(default=None, ge=0, le=100)
    reps: Optional[int] = Field(default=None, ge=0, le=1000)
    weight: Optional[float] = Field(default=None, ge=0, le=5000)
    distance: Optional[float] = Field(default=None, ge=0, le=1000)
    time: Optional[float] = Field(default=None, ge=0, le=10000)
    user: Optional[str] = Field(default=None, min_length=1, max_length=64)


class ExerciseInDB(ExerciseBase):
    """What an exercise log looks like when read from the database."""

    id: int
    session_id: str
    timestamp: str


class Exercise(ExerciseBase, table=True):
    """Database table for recorded exercises."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
