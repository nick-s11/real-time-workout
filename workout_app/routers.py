import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import select

from workout_app.db import database
from workout_app.models import Exercise, ExerciseCreate, WorkoutSession
from workout_app.realtime import connections, participants

router = APIRouter()


@router.post("/workouts", status_code=201)
def create_workout():
    session_id = str(uuid.uuid4())[:8]
    workout = WorkoutSession(session_id=session_id)
    with database.get_session() as session:
        session.add(workout)
        session.commit()

    connections[session_id] = []
    participants[session_id] = []
    return {"session_id": session_id}


@router.post("/workouts/{session_id}/join")
async def join_workout(session_id: str, user: str):
    participants.setdefault(session_id, [])
    if user not in participants[session_id]:
        participants[session_id].append(user)

    for conn in connections.get(session_id, []):
        await conn.send_json({"type": "participants", "data": participants[session_id]})
    return {"participants": participants[session_id]}


@router.get("/workouts/{session_id}")
def get_workout(session_id: str):
    with database.get_session() as session:
        exercises = session.exec(select(Exercise).where(Exercise.session_id == session_id)).all()
    return {"exercises": exercises}


@router.get("/history")
def get_all_sessions():
    with database.get_session() as session:
        sessions = session.exec(select(WorkoutSession).order_by(WorkoutSession.created_at.desc())).all()
    return {"sessions": sessions}


@router.post("/workouts/{session_id}/log", status_code=201)
async def log_exercise(session_id: str, exercise: ExerciseCreate):
    db_exercise = Exercise(**exercise.model_dump(), session_id=session_id)
    with database.get_session() as session:
        session.add(db_exercise)
        session.commit()
        session.refresh(db_exercise)

    if session_id in connections:
        for conn in connections[session_id]:
            await conn.send_json(db_exercise.model_dump())
    return db_exercise


@router.delete("/workouts/{session_id}")
def archive_workout(session_id: str):
    with database.get_session() as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Not found")
        db_session.active = False
        session.add(db_session)
        session.commit()

    connections.pop(session_id, None)
    participants.pop(session_id, None)
    return {"message": "Session archived"}


@router.websocket("/ws/workout/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connections.setdefault(session_id, []).append(websocket)
    await websocket.send_json({"type": "participants", "data": participants.get(session_id, [])})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if session_id in connections:
            connections[session_id].remove(websocket)
