"""In-memory WebSocket connection registry.

`connections` maps `session_id` to a list of connected `WebSocket`
objects so the application can broadcast live updates to clients.

Note: This in-memory approach is intentionally simple and suitable for
single-process development; for production or multi-worker deployments
use a shared pub/sub system (Redis, etc.).
"""

from typing import Dict, List

from fastapi import WebSocket

connections: Dict[str, List[WebSocket]] = {}
