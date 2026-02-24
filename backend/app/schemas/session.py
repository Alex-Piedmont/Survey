from datetime import date, datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    section_id: str
    presentation_type_id: str
    presenting_team_ids: list[str] = Field(min_length=1)
    session_date: date
    deadline: datetime | None = None  # Defaults to session_date 23:59 + 30 min grace


class SessionResponse(BaseModel):
    id: str
    section_id: str
    presentation_type_id: str
    template_snapshot_id: str
    session_date: date
    deadline: datetime
    status: str
    created_at: datetime
    presenting_team_ids: list[str] = []

    model_config = {"from_attributes": True}


class QRCodeResponse(BaseModel):
    session_id: str
    qr_url: str
    qr_base64: str


class StudentSessionResponse(BaseModel):
    """What a student sees when they scan the QR code."""
    session_id: str
    course_name: str
    section_name: str
    presentation_type_name: str
    session_date: date
    deadline: datetime
    status: str
    presenting_teams: list[dict]  # [{id, name, members}]
    questions: list[dict]  # Questions from the template snapshot
    student_role: str  # "audience" or "presenter"
    student_team_id: str | None = None  # If presenter, their team
