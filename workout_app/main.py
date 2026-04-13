from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from workout_app.db import database
from workout_app.routers import router as workout_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	await database.connect_to_database()
	try:
		yield
	finally:
		await database.close_database_connection()


app = FastAPI(lifespan=lifespan)

app.include_router(workout_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")