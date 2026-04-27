"""Application entry point for ASGI servers.

This module exposes the FastAPI `app` instance so Uvicorn and other ASGI
servers can import and run the application.
"""

from workout_app.main import app