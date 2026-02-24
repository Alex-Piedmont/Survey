from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enrollment import Enrollment
from app.models.presentation_grade import PresentationGrade
from app.models.section import Section
from app.models.session import Session, SessionTeam
from app.models.submission import Submission
from app.models.survey import PresentationType
from app.models.team import Team
from app.models.user import User
from app.schemas.dashboard import (
    CommentEntry,
    DashboardResponse,
    InstructorFeedbackCreate,
    ParticipationEntry,
    PresentationGradeCreate,
    PresentationGradeResponse,
    SessionListItem,
    SummaryResponse,
    TeamComments,
    TeamScoreSummary,
)
from app.services.aggregations import (
    aggregate_team_scores,
    build_participation_matrix,
    collect_free_text_comments,
    get_enrolled_count,
    get_enrolled_student_emails,
    get_latest_submissions,
    get_submitted_emails,
)

router = APIRouter(tags=["dashboard"])


async def _get_session_with_teams(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.session_teams))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _require_instructor(db: AsyncSession, session: Session, email: str):
    """Verify the user is an instructor for this session's course."""
    section = await db.execute(select(Section).where(Section.id == session.section_id))
    section = section.scalar_one()

    result = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == section.course_id,
            Enrollment.student_email == email,
            Enrollment.role.in_(["instructor", "ta"]),
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and TAs can access this resource",
        )


async def _get_team_names(db: AsyncSession, team_ids: list[str]) -> dict[str, str]:
    """Get team names for a list of team IDs."""
    if not team_ids:
        return {}
    result = await db.execute(select(Team).where(Team.id.in_(team_ids)))
    return {t.id: t.name for t in result.scalars().all()}


@router.get(
    "/api/v1/sessions/{session_id}/dashboard",
    response_model=DashboardResponse,
)
async def get_dashboard(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Live dashboard data: submission progress and per-team averages."""
    session = await _get_session_with_teams(db, session_id)
    await _require_instructor(db, session, current_user.email)

    enrolled_count = await get_enrolled_count(db, session.section_id)
    submitted = await get_submitted_emails(db, session_id)
    all_enrolled = await get_enrolled_student_emails(db, session.section_id)
    not_submitted = sorted(all_enrolled - submitted)

    team_ids = [st.team_id for st in session.session_teams]
    team_names = await _get_team_names(db, team_ids)

    scores = await aggregate_team_scores(db, session_id, session.template_snapshot_id)

    team_averages = []
    for tid in team_ids:
        team_averages.append(TeamScoreSummary(
            team_id=tid,
            team_name=team_names.get(tid, "Unknown"),
            scores=scores.get(tid, {}),
        ))

    return DashboardResponse(
        session_id=session_id,
        enrolled_count=enrolled_count,
        submitted_count=len(submitted),
        submitted_emails=sorted(submitted),
        not_submitted_emails=not_submitted,
        team_averages=team_averages,
    )


@router.get(
    "/api/v1/sessions/{session_id}/summary",
    response_model=SummaryResponse,
)
async def get_summary(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full session summary: scores, comments, participation, grades."""
    session = await _get_session_with_teams(db, session_id)
    await _require_instructor(db, session, current_user.email)

    team_ids = [st.team_id for st in session.session_teams]
    team_names = await _get_team_names(db, team_ids)

    # Aggregated scores
    scores = await aggregate_team_scores(db, session_id, session.template_snapshot_id)
    team_scores = [
        TeamScoreSummary(
            team_id=tid,
            team_name=team_names.get(tid, "Unknown"),
            scores=scores.get(tid, {}),
        )
        for tid in team_ids
    ]

    # Free-text comments
    raw_comments = await collect_free_text_comments(
        db, session_id, session.template_snapshot_id
    )
    team_comments = [
        TeamComments(
            team_id=tid,
            team_name=team_names.get(tid, "Unknown"),
            comments=[CommentEntry(**c) for c in raw_comments.get(tid, [])],
        )
        for tid in team_ids
    ]

    # Participation matrix
    matrix = await build_participation_matrix(db, session_id, session.section_id)
    participation = [ParticipationEntry(**m) for m in matrix]

    # Presentation grades
    result = await db.execute(
        select(PresentationGrade).where(PresentationGrade.session_id == session_id)
    )
    grades = [
        PresentationGradeResponse.model_validate(g)
        for g in result.scalars().all()
    ]

    # Instructor's own submissions
    instructor_subs = await get_latest_submissions(db, session_id)
    instructor_feedback = [
        {
            "target_team_id": s.target_team_id,
            "responses": s.responses,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        }
        for s in instructor_subs
        if s.feedback_type == "instructor"
    ]

    return SummaryResponse(
        session_id=session_id,
        session_date=session.session_date,
        team_scores=team_scores,
        team_comments=team_comments,
        participation_matrix=participation,
        presentation_grades=grades,
        instructor_submissions=instructor_feedback,
    )


@router.post(
    "/api/v1/sessions/{session_id}/instructor-feedback",
    status_code=status.HTTP_201_CREATED,
)
async def submit_instructor_feedback(
    session_id: str,
    body: InstructorFeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instructor submits their own feedback for a presenting team."""
    session = await _get_session_with_teams(db, session_id)
    await _require_instructor(db, session, current_user.email)

    # Verify target team is presenting
    presenting_ids = {st.team_id for st in session.session_teams}
    if body.target_team_id not in presenting_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target team is not presenting in this session",
        )

    # Check for existing instructor feedback (upsert via version)
    version_result = await db.execute(
        select(func.max(Submission.version)).where(
            Submission.session_id == session_id,
            Submission.student_email == current_user.email,
            Submission.target_team_id == body.target_team_id,
            Submission.feedback_type == "instructor",
        )
    )
    current_max = version_result.scalar_one_or_none() or 0

    submission = Submission(
        session_id=session_id,
        student_email=current_user.email,
        target_team_id=body.target_team_id,
        feedback_type="instructor",
        responses=body.responses,
        version=current_max + 1,
        submitted_at=datetime.now(timezone.utc),
        is_late=False,
        penalty_pct=0,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return {"id": submission.id, "version": submission.version}


@router.post(
    "/api/v1/sessions/{session_id}/teams/{team_id}/presentation-grade",
    response_model=PresentationGradeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_presentation_grade(
    session_id: str,
    team_id: str,
    body: PresentationGradeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instructor assigns a presentation quality grade to a team."""
    session = await _get_session_with_teams(db, session_id)
    await _require_instructor(db, session, current_user.email)

    presenting_ids = {st.team_id for st in session.session_teams}
    if team_id not in presenting_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team is not presenting in this session",
        )

    # Upsert: delete existing grade and create new one
    existing = await db.execute(
        select(PresentationGrade).where(
            PresentationGrade.session_id == session_id,
            PresentationGrade.team_id == team_id,
        )
    )
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)
        await db.flush()

    grade = PresentationGrade(
        session_id=session_id,
        team_id=team_id,
        grade=body.grade,
        comments=body.comments,
        graded_by=current_user.email,
    )
    db.add(grade)
    await db.commit()
    await db.refresh(grade)

    return PresentationGradeResponse.model_validate(grade)


@router.put("/api/v1/sessions/{session_id}/comments/{submission_id}/withhold")
async def withhold_comment(
    session_id: str,
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle withhold status on a submission's comments."""
    session = await _get_session_with_teams(db, session_id)
    await _require_instructor(db, session, current_user.email)

    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.session_id == session_id,
        )
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    submission.withheld = not submission.withheld
    await db.commit()

    return {"submission_id": submission_id, "withheld": submission.withheld}


@router.get(
    "/api/v1/sections/{section_id}/sessions",
    response_model=list[SessionListItem],
)
async def list_sessions(
    section_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all sessions for a section."""
    # Verify access
    section = await db.execute(select(Section).where(Section.id == section_id))
    section_obj = section.scalar_one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
        )

    result = await db.execute(
        select(Enrollment).where(
            Enrollment.section_id == section_id,
            Enrollment.student_email == current_user.email,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this section",
        )

    # Get sessions with counts
    sessions = await db.execute(
        select(Session)
        .options(selectinload(Session.session_teams))
        .where(Session.section_id == section_id)
        .order_by(Session.session_date.desc())
    )
    sessions = sessions.scalars().all()

    items = []
    for s in sessions:
        # Get submission count
        sub_count = await db.execute(
            select(func.count(func.distinct(Submission.student_email))).where(
                Submission.session_id == s.id
            )
        )
        # Get presentation type name
        ptype = await db.execute(
            select(PresentationType).where(PresentationType.id == s.presentation_type_id)
        )
        ptype_obj = ptype.scalar_one()

        items.append(SessionListItem(
            id=s.id,
            presentation_type_id=s.presentation_type_id,
            presentation_type_name=ptype_obj.name,
            session_date=s.session_date,
            deadline=s.deadline,
            status=s.status,
            created_at=s.created_at,
            presenting_team_count=len(s.session_teams),
            submission_count=sub_count.scalar_one(),
        ))

    return items


@router.get("/api/v1/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export session data as CSV or XLSX."""
    session = await _get_session_with_teams(db, session_id)
    await _require_instructor(db, session, current_user.email)

    from app.services.exports import export_session_csv, export_session_xlsx

    if format == "csv":
        content = await export_session_csv(db, session_id)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"},
        )
    else:
        content = await export_session_xlsx(db, session_id)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.xlsx"},
        )
