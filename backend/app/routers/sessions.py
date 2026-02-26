import base64
import io
from datetime import datetime, time, timedelta, timezone

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_access_token
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.session import Session, SessionTeam
from app.models.survey import PresentationType, Question, SurveyTemplate
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.session import (
    QRCodeResponse,
    SessionCreate,
    SessionResponse,
    StudentSessionResponse,
)

router = APIRouter(tags=["sessions"])


def _generate_qr_base64(url: str) -> str:
    """Generate a QR code PNG as base64 string."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


async def _snapshot_template(
    db: AsyncSession, presentation_type_id: str
) -> SurveyTemplate:
    """Create a frozen copy of the latest template version (FR-12)."""
    result = await db.execute(
        select(SurveyTemplate)
        .options(selectinload(SurveyTemplate.questions))
        .where(SurveyTemplate.presentation_type_id == presentation_type_id)
        .order_by(SurveyTemplate.version.desc())
        .limit(1)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No template exists for this presentation type",
        )

    # Create snapshot with negative version to distinguish from editable versions
    snapshot = SurveyTemplate(
        presentation_type_id=presentation_type_id,
        version=-(source.version),  # Negative = snapshot
    )
    db.add(snapshot)
    await db.flush()

    # Copy all active questions
    for q in source.questions:
        if q.is_active:
            db.add(Question(
                template_id=snapshot.id,
                question_text=q.question_text,
                question_type=q.question_type,
                category=q.category,
                options=q.options,
                is_required=q.is_required,
                sort_order=q.sort_order,
                is_active=True,
            ))

    await db.flush()
    return snapshot


@router.post(
    "/api/v1/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a session with template snapshot and QR code."""
    if not current_user.is_instructor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor privileges required",
        )

    # Verify instructor for this section's course
    section = await db.execute(select(Section).where(Section.id == body.section_id))
    section = section.scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == section.course_id,
            Enrollment.student_email == current_user.email,
            Enrollment.role == "instructor",
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can create sessions",
        )

    # Snapshot the template
    snapshot = await _snapshot_template(db, body.presentation_type_id)

    # Calculate deadline: default is session_date 23:59 + 30 min grace
    if body.deadline:
        deadline = body.deadline
    else:
        deadline = datetime.combine(
            body.session_date,
            time(23, 59, tzinfo=timezone.utc),
        ) + timedelta(minutes=30)

    session = Session(
        section_id=body.section_id,
        presentation_type_id=body.presentation_type_id,
        template_snapshot_id=snapshot.id,
        session_date=body.session_date,
        deadline=deadline,
    )
    db.add(session)
    await db.flush()

    # Link presenting teams
    for team_id in body.presenting_team_ids:
        # Verify team exists and belongs to this section
        team = await db.execute(
            select(Team).where(Team.id == team_id, Team.section_id == body.section_id)
        )
        if team.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {team_id} not found in this section",
            )
        db.add(SessionTeam(session_id=session.id, team_id=team_id))

    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        section_id=session.section_id,
        presentation_type_id=session.presentation_type_id,
        template_snapshot_id=session.template_snapshot_id,
        session_date=session.session_date,
        deadline=session.deadline,
        status=session.status,
        created_at=session.created_at,
        presenting_team_ids=body.presenting_team_ids,
    )


@router.get("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get session details."""
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.session_teams))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return SessionResponse(
        id=session.id,
        section_id=session.section_id,
        presentation_type_id=session.presentation_type_id,
        template_snapshot_id=session.template_snapshot_id,
        session_date=session.session_date,
        deadline=session.deadline,
        status=session.status,
        created_at=session.created_at,
        presenting_team_ids=[st.team_id for st in session.session_teams],
    )


@router.get("/api/v1/sessions/{session_id}/qr", response_model=QRCodeResponse)
async def get_qr_code(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get QR code for a session as base64 PNG."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    qr_url = f"{settings.FRONTEND_URL}/s/{session.id}"
    qr_base64 = _generate_qr_base64(qr_url)

    return QRCodeResponse(session_id=session.id, qr_url=qr_url, qr_base64=qr_base64)


_optional_bearer = HTTPBearer(auto_error=False)


@router.get("/api/v1/s/{session_id}", response_model=StudentSessionResponse)
async def get_student_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
):
    """Student-facing endpoint: get session form data. Auth optional (FR-14).
    If authenticated, returns student_role and student_team_id."""
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.session_teams))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get course and section info
    section = await db.execute(select(Section).where(Section.id == session.section_id))
    section = section.scalar_one()
    course = await db.execute(select(Course).where(Course.id == section.course_id))
    course = course.scalar_one()
    ptype = await db.execute(
        select(PresentationType).where(PresentationType.id == session.presentation_type_id)
    )
    ptype = ptype.scalar_one()

    # Get template snapshot questions
    template = await db.execute(
        select(SurveyTemplate)
        .options(selectinload(SurveyTemplate.questions))
        .where(SurveyTemplate.id == session.template_snapshot_id)
    )
    template = template.scalar_one()

    # Get presenting teams with members
    presenting_teams = []
    team_members: dict[str, list[str]] = {}
    for st in session.session_teams:
        team = await db.execute(
            select(Team)
            .options(selectinload(Team.memberships))
            .where(Team.id == st.team_id)
        )
        team = team.scalar_one()
        members = [m.student_email for m in team.memberships]
        team_members[team.id] = members
        presenting_teams.append({
            "id": team.id,
            "name": team.name,
            "members": members,
        })

    questions = [
        {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "category": q.category,
            "options": q.options,
            "is_required": q.is_required,
            "sort_order": q.sort_order,
        }
        for q in sorted(template.questions, key=lambda q: q.sort_order)
        if q.is_active
    ]

    # Detect student role from optional auth
    student_role = "audience"
    student_team_id = None
    if credentials:
        payload = verify_access_token(credentials.credentials)
        if payload:
            email = payload["sub"]
            for tid, members in team_members.items():
                if email in members:
                    student_role = "presenter"
                    student_team_id = tid
                    break

    return StudentSessionResponse(
        session_id=session.id,
        course_name=course.name,
        section_name=section.name,
        presentation_type_name=ptype.name,
        session_date=session.session_date,
        deadline=session.deadline,
        status=session.status,
        presenting_teams=presenting_teams,
        questions=questions,
        student_role=student_role,
        student_team_id=student_team_id,
    )
