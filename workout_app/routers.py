import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from workout_app.db import database
from workout_app.models import (
    Exercise,
    ExerciseCreate,
    JoinWorkoutRequest,
    SessionParticipant,
    User,
    WorkoutSession,
)
from workout_app.realtime import connections

router = APIRouter()


def _get_or_create_user(session, name: str) -> User:
    user = session.exec(select(User).where(User.name == name)).first()
    if user:
        return user

    user = User(name=name)
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        user = session.exec(select(User).where(User.name == name)).first()
        if not user:
            raise HTTPException(status_code=500, detail="Could not create or load user")
    return user


def _participant_names(session, session_id: str) -> list[str]:
    statement = (
        select(User.name)
        .join(SessionParticipant, SessionParticipant.user_id == User.id)
        .where(SessionParticipant.session_id == session_id)
        .order_by(User.name)
    )
    return list(session.exec(statement).all())


async def _broadcast(session_id: str, payload: dict):
    stale_connections = []
    for conn in connections.get(session_id, []):
        try:
            await conn.send_json(payload)
        except Exception:
            stale_connections.append(conn)

    if stale_connections:
        connections[session_id] = [conn for conn in connections.get(session_id, []) if conn not in stale_connections]


@router.post("/workouts", status_code=201)
def create_workout():
    session_id = str(uuid.uuid4())[:8]
    workout = WorkoutSession(session_id=session_id)
    with database.get_session() as session:
        session.add(workout)
        session.commit()

    connections[session_id] = []
    return {"session_id": session_id}


@router.post("/workouts/{session_id}/join")
async def join_workout(session_id: str, payload: JoinWorkoutRequest):
    with database.get_session() as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session or not db_session.active:
            raise HTTPException(status_code=404, detail="Session not found or inactive")

        user = _get_or_create_user(session, payload.name)

        existing = session.exec(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == user.id,
            )
        ).first()
        if not existing:
            session.add(SessionParticipant(session_id=session_id, user_id=user.id))
            session.commit()

        participants = _participant_names(session, session_id)

    await _broadcast(session_id, {"type": "participants", "data": participants})
    return {"session_id": session_id, "participants": participants}


@router.get("/workouts/{session_id}")
def get_workout(session_id: str):
    with database.get_session() as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        exercises = session.exec(select(Exercise).where(Exercise.session_id == session_id)).all()
        participants = _participant_names(session, session_id)
    return {"session": db_session, "participants": participants, "exercises": exercises}


@router.get("/history")
def get_all_sessions():
    with database.get_session() as session:
        sessions = session.exec(select(WorkoutSession).order_by(WorkoutSession.created_at.desc())).all()
    return {"sessions": sessions}


@router.post("/workouts/{session_id}/log", status_code=201)
async def log_exercise(session_id: str, exercise: ExerciseCreate):
    participant_added = False
    with database.get_session() as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session or not db_session.active:
            raise HTTPException(status_code=404, detail="Session not found or inactive")

        user = _get_or_create_user(session, exercise.user)
        existing = session.exec(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == user.id,
            )
        ).first()
        if not existing:
            session.add(SessionParticipant(session_id=session_id, user_id=user.id))
            participant_added = True

        db_exercise = Exercise(**exercise.model_dump(), session_id=session_id)
        session.add(db_exercise)
        session.commit()
        session.refresh(db_exercise)
        participants = _participant_names(session, session_id)

    if participant_added:
        await _broadcast(session_id, {"type": "participants", "data": participants})

    await _broadcast(session_id, db_exercise.model_dump())
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
    return {"message": "Session archived"}


@router.websocket("/ws/workout/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    with database.get_session() as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session or not db_session.active:
            await websocket.send_json({"type": "error", "detail": "Session not found or inactive"})
            await websocket.close(code=1008)
            return

        participant_names = _participant_names(session, session_id)

    connections.setdefault(session_id, []).append(websocket)
    await websocket.send_json({"type": "participants", "data": participant_names})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if session_id in connections and websocket in connections[session_id]:
            connections[session_id].remove(websocket)
