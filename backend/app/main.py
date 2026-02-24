from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, courses, enrollments, feedback, sessions, surveys, teams

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


@app.get("/health")
async def health():
    return {"status": "ok"}
