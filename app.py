from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import List, Dict, Optional
from datetime import datetime
import uuid

app = FastAPI()

# -----------------------
# DATABASE & MODELS
# -----------------------
engine = create_engine("sqlite:///database.db")

class WorkoutSession(SQLModel, table=True):
    session_id: str = Field(primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    active: bool = True

class Exercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str  # "lifting" or "cardio"
    name: str
    sets: int = 0
    reps: int = 0
    weight: float = 0.0
    distance: float = 0.0
    time: float = 0.0
    user: str
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

SQLModel.metadata.create_all(engine)

# -----------------------
# REAL-TIME STORAGE
# -----------------------
connections: Dict[str, List[WebSocket]] = {}
participants: Dict[str, List[str]] = {}

# -----------------------
# API ROUTES
# -----------------------

@app.post("/workouts", status_code=201)
def create_workout():
    session_id = str(uuid.uuid4())[:8]
    workout = WorkoutSession(session_id=session_id)
    with Session(engine) as session:
        session.add(workout)
        session.commit()
    
    connections[session_id] = []
    participants[session_id] = []
    return {"session_id": session_id}

@app.post("/workouts/{session_id}/join")
async def join_workout(session_id: str, user: str):
    participants.setdefault(session_id, [])
    if user not in participants[session_id]:
        participants[session_id].append(user)

    for conn in connections.get(session_id, []):
        await conn.send_json({"type": "participants", "data": participants[session_id]})
    return {"participants": participants[session_id]}

@app.get("/workouts/{session_id}")
def get_workout(session_id: str):
    with Session(engine) as session:
        exercises = session.exec(select(Exercise).where(Exercise.session_id == session_id)).all()
    return {"exercises": exercises}

@app.get("/history")
def get_all_sessions():
    with Session(engine) as session:
        # Returns all sessions, newest first
        sessions = session.exec(select(WorkoutSession).order_by(WorkoutSession.created_at.desc())).all()
    return {"sessions": sessions}

@app.post("/workouts/{session_id}/log", status_code=201)
async def log_exercise(session_id: str, exercise: Exercise):
    exercise.session_id = session_id
    with Session(engine) as session:
        session.add(exercise)
        session.commit()
        session.refresh(exercise)

    if session_id in connections:
        for conn in connections[session_id]:
            await conn.send_json(exercise.model_dump())
    return exercise

@app.delete("/workouts/{session_id}")
def archive_workout(session_id: str):
    with Session(engine) as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Not found")
        db_session.active = False # Archive instead of hard delete
        session.add(db_session)
        session.commit()
    
    connections.pop(session_id, None)
    participants.pop(session_id, None)
    return {"message": "Session archived"}

# -----------------------
# WEBSOCKET
# -----------------------

@app.websocket("/ws/workout/{session_id}")
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

app.mount("/", StaticFiles(directory="static", html=True), name="static")