from datetime import date, datetime

from pydantic import BaseModel


class TeamScoreSummary(BaseModel):
    team_id: str
    team_name: str
    scores: dict[str, dict]  # {question_id: {mean, median, std_dev, count, histogram}}


class DashboardResponse(BaseModel):
    session_id: str
    enrolled_count: int
    submitted_count: int
    submitted_emails: list[str]
    not_submitted_emails: list[str]
    team_averages: list[TeamScoreSummary]


class CommentEntry(BaseModel):
    question_id: str
    question_text: str = ""
    text: str
    submission_id: str
    withheld: bool


class TeamComments(BaseModel):
    team_id: str
    team_name: str
    comments: list[CommentEntry]


class ParticipationEntry(BaseModel):
    email: str
    audience_submissions: dict[str, bool]  # {team_id: submitted?}
    peer_submitted: bool
    is_presenter: bool


class PresentationGradeResponse(BaseModel):
    id: str
    session_id: str
    team_id: str
    grade: str
    comments: str | None
    graded_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    session_id: str
    session_date: date
    team_scores: list[TeamScoreSummary]
    team_comments: list[TeamComments]
    participation_matrix: list[ParticipationEntry]
    presentation_grades: list[PresentationGradeResponse]
    instructor_submissions: list[dict]  # Instructor's own feedback


class InstructorFeedbackCreate(BaseModel):
    target_team_id: str
    responses: dict  # {question_id: value}


class PresentationGradeCreate(BaseModel):
    grade: str
    comments: str | None = None


class SessionListItem(BaseModel):
    id: str
    presentation_type_id: str
    presentation_type_name: str
    session_date: date
    deadline: datetime
    status: str
    created_at: datetime
    presenting_team_count: int
    submission_count: int
