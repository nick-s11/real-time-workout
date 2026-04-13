from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class WorkoutSession(SQLModel, table=True):
    session_id: str = Field(primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    active: bool = True


class ExerciseBase(SQLModel):
    type: str
    name: str
    sets: int = 0
    reps: int = 0
    weight: float = 0.0
    distance: float = 0.0
    time: float = 0.0
    user: str


class ExerciseCreate(ExerciseBase):
    """Shape of data when creating a new exercise log."""


class ExerciseUpdate(SQLModel):
    """Fields that can be updated; all optional."""

    type: Optional[str] = None
    name: Optional[str] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight: Optional[float] = None
    distance: Optional[float] = None
    time: Optional[float] = None
    user: Optional[str] = None


class ExerciseInDB(ExerciseBase):
    """What an exercise log looks like when read from the database."""

    id: int
    session_id: str
    timestamp: str


class Exercise(ExerciseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
