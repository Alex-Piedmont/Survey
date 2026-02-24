from datetime import datetime

from pydantic import BaseModel


class SubmitFeedback(BaseModel):
    target_team_id: str | None = None
    target_student_email: str | None = None
    feedback_type: str  # "audience" or "peer"
    responses: dict  # {question_id: answer}


class SubmissionResponse(BaseModel):
    id: str
    session_id: str
    student_email: str
    target_team_id: str | None
    target_student_email: str | None
    feedback_type: str
    responses: dict
    version: int
    submitted_at: datetime
    is_late: bool
    penalty_pct: int

    model_config = {"from_attributes": True}


class ParticipationResponse(BaseModel):
    student_email: str
    session_id: str
    audience_credit: float  # 0.0 to 1.0
    peer_credit: float | None  # None if not a presenter
    is_presenter: bool
