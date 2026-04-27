"""Database helpers.

This module creates the SQLModel engine and provides a simple `Database`
helper with lifecycle methods used by the FastAPI lifespan manager.
"""

from sqlmodel import Session, SQLModel, create_engine

from workout_app.config import DATABASE_OPTIONS, DATABASE_URL


class Database:
    """Encapsulate SQLModel engine and session creation.

    Methods:
    - `connect_to_database`: Create tables (invoked at app startup).
    - `close_database_connection`: Dispose engine (invoked at shutdown).
    - `get_session`: Return a new `Session` for DB operations.
    """

    def __init__(self) -> None:
        self.engine = create_engine(DATABASE_URL, **DATABASE_OPTIONS)

    async def connect_to_database(self) -> None:
        """Create all database tables.

        This is synchronous in SQLModel, but the method is `async` so it
        can be awaited by FastAPI lifespan handlers.
        """
        SQLModel.metadata.create_all(self.engine)

    async def close_database_connection(self) -> None:
        """Dispose the underlying engine and release resources."""
        self.engine.dispose()

    def get_session(self) -> Session:
        """Return a new SQLModel `Session` bound to the engine."""
        return Session(self.engine)


database = Database()
