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

    # Broadcast updated participant list
    for conn in connections.get(session_id, []):
        await conn.send_json({"type": "participants", "data": participants[session_id]})
    
    return {"participants": participants[session_id]}

@app.get("/workouts/{session_id}")
def get_workout(session_id: str):
    with Session(engine) as session:
        # Check if session exists
        stmt = select(WorkoutSession).where(WorkoutSession.session_id == session_id)
        db_session = session.exec(stmt).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        exercises = session.exec(
            select(Exercise).where(Exercise.session_id == session_id)
        ).all()
    return {"session": db_session, "exercises": exercises}

@app.post("/workouts/{session_id}/log", status_code=201)
async def log_exercise(session_id: str, exercise: Exercise):
    # Set the session ID from URL to the exercise object
    exercise.session_id = session_id
    
    with Session(engine) as session:
        session.add(exercise)
        session.commit()
        session.refresh(exercise)

    # Broadcast update
    if session_id in connections:
        for conn in connections[session_id]:
            await conn.send_json(exercise.model_dump())
    
    return exercise

@app.delete("/workouts/{session_id}")
def delete_workout(session_id: str):
    with Session(engine) as session:
        db_session = session.get(WorkoutSession, session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # We can either delete or just set active=False per requirements
        session.delete(db_session)
        session.commit()
    
    # Cleanup memory
    connections.pop(session_id, None)
    participants.pop(session_id, None)
    
    return {"message": "Session ended and deleted"}

# -----------------------
# WEBSOCKET
# -----------------------

@app.websocket("/ws/workout/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connections.setdefault(session_id, []).append(websocket)

    await websocket.send_json({
        "type": "participants",
        "data": participants.get(session_id, [])
    })

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if session_id in connections:
            connections[session_id].remove(websocket)

# -----------------------
# STATIC FILES (Last)
# -----------------------
app.mount("/", StaticFiles(directory="static", html=True), name="static")