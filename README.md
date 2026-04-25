# Real-Time Workout Logger

Real-Time Workout Logger is a small FastAPI app for creating workout sessions, logging exercises, and sharing live updates with everyone connected to the same session.

The project serves a single-page frontend from `static/index.html` and uses SQLite for persistence. Live participant and exercise updates are delivered over WebSockets.

## Features

- Create a new workout session with a short session ID.
- Join an existing session by ID and username.
- Log lifting or cardio exercises into a live feed.
- Broadcast participant changes and new exercise entries in real time.
- View archived workout sessions from the history list.

## Tech Stack

- FastAPI
- Uvicorn
- SQLModel
- SQLite

## Project Structure

- `app.py` - Application entry point.
- `workout_app/main.py` - FastAPI app setup and static file mounting.
- `workout_app/routers.py` - REST API and WebSocket routes.
- `workout_app/models.py` - Database models and request schemas.
- `workout_app/db.py` - Database engine and session helpers.
- `workout_app/config.py` - Database configuration.
- `static/index.html` - Frontend UI.

## Requirements

- Python 3.10 or newer is recommended.
- `pip` for dependency installation.

## Installation

1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

## Running the App

Start the development server with Uvicorn:

```bash
uvicorn app:app --reload
```

Then open the app in your browser at `http://127.0.0.1:8000`.

## How It Works

1. Create a session with the "Create New Session" button.
2. Share the session ID with other users.
3. Join the session with a name and start logging exercises.
4. Keep the page open to see live participant updates and exercise logs.

## API Endpoints

- `POST /workouts` - Create a new workout session.
- `POST /workouts/{session_id}/join?user=Name` - Join a session.
- `GET /workouts/{session_id}` - Fetch exercises for a session.
- `POST /workouts/{session_id}/log` - Add an exercise entry.
- `DELETE /workouts/{session_id}` - Archive a session.
- `GET /history` - List all workout sessions.
- `WS /ws/workout/{session_id}` - Stream participant and exercise updates.

## Database

The app uses a local SQLite database file at `database.db`. Tables are created automatically on startup.

## Notes

- The frontend is intentionally simple and self-contained.
- Archived sessions stay in history, but live connections are cleared when a session is archived.
