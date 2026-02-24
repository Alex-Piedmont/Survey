from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.session import Session, SessionTeam
from app.models.submission import Submission
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.submission import SubmissionResponse, SubmitFeedback
from app.services.penalties import calculate_penalty
from app.ws.manager import manager

router = APIRouter(tags=["feedback"])


async def _get_session_or_404(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.session_teams))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _validate_enrollment(db: AsyncSession, session: Session, email: str):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.section_id == session.section_id,
            Enrollment.student_email == email,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this section. Contact your instructor.",
        )


async def _get_student_team(db: AsyncSession, session: Session, email: str) -> str | None:
    """Check if student is on a presenting team. Returns team_id or None."""
    presenting_team_ids = [st.team_id for st in session.session_teams]
    if not presenting_team_ids:
        return None

    result = await db.execute(
        select(TeamMembership.team_id).where(
            TeamMembership.student_email == email,
            TeamMembership.team_id.in_(presenting_team_ids),
        )
    )
    row = result.first()
    return row[0] if row else None


def _check_submission_window(session: Session):
    """Check if we're within the 7-day submission window."""
    now = datetime.now(timezone.utc)
    session_date = session.session_date
    if isinstance(session_date, str):
        session_date = date.fromisoformat(session_date)
    window_end = datetime.combine(
        session_date, datetime.min.time(), tzinfo=timezone.utc
    ) + timedelta(days=7)

    if now > window_end:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The submission window for this session has closed.",
        )


@router.post(
    "/api/v1/s/{session_id}/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    session_id: str,
    body: SubmitFeedback,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback for one target (per-page save, FR-16a).
    Creates a new submission or a new version if one already exists."""
    session = await _get_session_or_404(db, session_id)
    await _validate_enrollment(db, session, current_user.email)
    _check_submission_window(session)

    now = datetime.now(timezone.utc)

    # Validate the target based on feedback type
    if body.feedback_type == "audience":
        if not body.target_team_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_team_id is required for audience feedback",
            )
        # Verify team is presenting in this session
        presenting_ids = {st.team_id for st in session.session_teams}
        if body.target_team_id not in presenting_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target team is not presenting in this session",
            )
        # Presenters can't give audience feedback to their own team
        student_team = await _get_student_team(db, session, current_user.email)
        if student_team == body.target_team_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot submit audience feedback for your own team",
            )

    elif body.feedback_type == "peer":
        if not body.target_student_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_student_email is required for peer feedback",
            )
        # Verify the submitter is on a presenting team
        student_team = await _get_student_team(db, session, current_user.email)
        if student_team is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only presenters can submit peer feedback",
            )
        # Verify target is on the same team
        result = await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == student_team,
                TeamMembership.student_email == body.target_student_email,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target student is not on your team",
            )
        # Can't rate yourself
        if body.target_student_email == current_user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Self-evaluation is not allowed",
            )
        body.target_team_id = student_team
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="feedback_type must be 'audience' or 'peer'",
        )

    # Calculate late penalty per target
    is_late, penalty_pct = calculate_penalty(session.deadline, now)
    if penalty_pct == -1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The submission window for this session has closed.",
        )

    # Determine version number (increment from latest for same target)
    version_result = await db.execute(
        select(func.max(Submission.version)).where(
            Submission.session_id == session_id,
            Submission.student_email == current_user.email,
            Submission.target_team_id == body.target_team_id,
            Submission.target_student_email == body.target_student_email,
        )
    )
    current_max = version_result.scalar_one_or_none() or 0

    submission = Submission(
        session_id=session_id,
        student_email=current_user.email,
        target_team_id=body.target_team_id,
        target_student_email=body.target_student_email,
        feedback_type=body.feedback_type,
        responses=body.responses,
        version=current_max + 1,
        submitted_at=now,
        is_late=is_late,
        penalty_pct=penalty_pct,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Broadcast to live dashboard
    await manager.broadcast(session_id, {
        "type": "new_submission",
        "student_email": current_user.email,
        "feedback_type": body.feedback_type,
        "target_team_id": body.target_team_id,
        "version": submission.version,
    })

    return SubmissionResponse.model_validate(submission)


@router.get(
    "/api/v1/s/{session_id}/submissions",
    response_model=list[SubmissionResponse],
)
async def get_my_submissions(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's submissions for a session (latest versions only)."""
    # Subquery: max version per target
    subq = (
        select(
            Submission.target_team_id,
            Submission.target_student_email,
            func.max(Submission.version).label("max_version"),
        )
        .where(
            Submission.session_id == session_id,
            Submission.student_email == current_user.email,
        )
        .group_by(Submission.target_team_id, Submission.target_student_email)
        .subquery()
    )

    result = await db.execute(
        select(Submission)
        .join(
            subq,
            (Submission.target_team_id == subq.c.target_team_id)
            & or_(
                Submission.target_student_email == subq.c.target_student_email,
                (Submission.target_student_email.is_(None)) & (subq.c.target_student_email.is_(None)),
            )
            & (Submission.version == subq.c.max_version),
        )
        .where(
            Submission.session_id == session_id,
            Submission.student_email == current_user.email,
        )
    )
    return [SubmissionResponse.model_validate(s) for s in result.scalars().all()]


@router.get(
    "/api/v1/me/submissions",
    response_model=list[SubmissionResponse],
)
async def get_all_my_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all submissions by the current user across all sessions."""
    result = await db.execute(
        select(Submission)
        .where(Submission.student_email == current_user.email)
        .order_by(Submission.submitted_at.desc())
    )
    return [SubmissionResponse.model_validate(s) for s in result.scalars().all()]
