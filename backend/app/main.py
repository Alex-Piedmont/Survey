from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, courses, dashboard, enrollments, feedback, sessions, surveys, teams

app = FastAPI(title="Classroom Survey Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(enrollments.router)
app.include_router(surveys.router)
app.include_router(teams.router)
app.include_router(sessions.router)
app.include_router(feedback.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# WebSocket endpoint for live dashboard
from fastapi import WebSocket, WebSocketDisconnect
from app.ws.manager import manager


@app.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive; client sends pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
