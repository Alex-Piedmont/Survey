"""WebSocket connection manager for live dashboard updates."""

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections grouped by session_id."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: dict):
        """Broadcast a message to all connections for a session."""
        if session_id not in self.active_connections:
            return
        disconnected = []
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(session_id, ws)


# Singleton instance
manager = ConnectionManager()
