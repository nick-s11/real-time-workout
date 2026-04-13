from sqlmodel import Session, SQLModel, create_engine

from workout_app.config import DATABASE_OPTIONS, DATABASE_URL


class Database:
    def __init__(self) -> None:
        self.engine = create_engine(DATABASE_URL, **DATABASE_OPTIONS)

    async def connect_to_database(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    async def close_database_connection(self) -> None:
        self.engine.dispose()

    def get_session(self) -> Session:
        return Session(self.engine)


database = Database()
