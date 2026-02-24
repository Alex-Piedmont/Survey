from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import SessionTeam
from app.models.submission import Submission
from app.models.team import TeamMembership


async def calculate_audience_participation(
    db: AsyncSession, session_id: str, student_email: str
) -> float:
    """Calculate audience participation credit as K/N where K = teams submitted for,
    N = total presenting teams. Returns 0.0 to 1.0."""
    # Total presenting teams in this session
    total = await db.execute(
        select(func.count()).where(SessionTeam.session_id == session_id)
    )
    total_teams = total.scalar_one()
    if total_teams == 0:
        return 0.0

    # Teams this student submitted audience feedback for (latest version per team)
    submitted = await db.execute(
        select(func.count(func.distinct(Submission.target_team_id))).where(
            Submission.session_id == session_id,
            Submission.student_email == student_email,
            Submission.feedback_type == "audience",
        )
    )
    submitted_count = submitted.scalar_one()

    return submitted_count / total_teams


async def calculate_peer_participation(
    db: AsyncSession, session_id: str, student_email: str, team_id: str
) -> float:
    """Calculate peer participation credit as K/N where K = team members given peer
    feedback, N = total team members (excluding self). Returns 0.0 to 1.0."""
    # Total team members excluding self
    total = await db.execute(
        select(func.count()).where(
            TeamMembership.team_id == team_id,
            TeamMembership.student_email != student_email,
        )
    )
    total_members = total.scalar_one()
    if total_members == 0:
        return 1.0  # No peers to review

    # Peers this student submitted peer feedback for
    submitted = await db.execute(
        select(func.count(func.distinct(Submission.target_student_email))).where(
            Submission.session_id == session_id,
            Submission.student_email == student_email,
            Submission.feedback_type == "peer",
        )
    )
    submitted_count = submitted.scalar_one()

    return submitted_count / total_members
