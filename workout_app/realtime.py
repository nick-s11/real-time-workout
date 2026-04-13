from typing import Dict, List

from fastapi import WebSocket

connections: Dict[str, List[WebSocket]] = {}
participants: Dict[str, List[str]] = {}
