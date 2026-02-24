from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberUpdate, TeamResponse

router = APIRouter(tags=["teams"])


async def _verify_section_instructor(db: AsyncSession, section_id: str, email: str) -> Section:
    result = await db.execute(select(Section).where(Section.id == section_id))
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == section.course_id,
            Enrollment.student_email == email,
            Enrollment.role == "instructor",
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can manage teams",
        )
    return section


def _team_to_response(team: Team) -> TeamResponse:
    members = [m.student_email for m in team.memberships] if team.memberships else []
    return TeamResponse(
        id=team.id,
        section_id=team.section_id,
        presentation_type_id=team.presentation_type_id,
        name=team.name,
        members=members,
    )


@router.post(
    "/api/v1/sections/{section_id}/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_team(
    section_id: str,
    body: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a team with optional initial members."""
    await _verify_section_instructor(db, section_id, current_user.email)

    team = Team(
        section_id=section_id,
        presentation_type_id=body.presentation_type_id,
        name=body.name,
    )
    db.add(team)
    await db.flush()

    # Add members (validate they're enrolled in this section)
    members_added = []
    for email in body.member_emails:
        email = email.strip().lower()
        enrollment = await db.execute(
            select(Enrollment).where(
                Enrollment.section_id == section_id,
                Enrollment.student_email == email,
            )
        )
        if enrollment.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{email} is not enrolled in this section",
            )
        db.add(TeamMembership(team_id=team.id, student_email=email))
        members_added.append(email)

    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id,
        section_id=team.section_id,
        presentation_type_id=team.presentation_type_id,
        name=team.name,
        members=members_added,
    )


@router.get(
    "/api/v1/sections/{section_id}/teams",
    response_model=list[TeamResponse],
)
async def list_teams(
    section_id: str,
    presentation_type_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List teams for a section, optionally filtered by presentation type."""
    query = (
        select(Team)
        .options(selectinload(Team.memberships))
        .where(Team.section_id == section_id)
    )
    if presentation_type_id:
        query = query.where(Team.presentation_type_id == presentation_type_id)

    result = await db.execute(query)
    teams = result.scalars().all()
    return [_team_to_response(t) for t in teams]


@router.put(
    "/api/v1/teams/{team_id}/members",
    response_model=TeamResponse,
)
async def update_team_members(
    team_id: str,
    body: TeamMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Replace team membership list."""
    result = await db.execute(
        select(Team).options(selectinload(Team.memberships)).where(Team.id == team_id)
    )
    team = result.scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    await _verify_section_instructor(db, team.section_id, current_user.email)

    # Remove existing memberships
    for m in team.memberships:
        await db.delete(m)
    await db.flush()

    # Add new memberships
    members_added = []
    for email in body.member_emails:
        email = email.strip().lower()
        enrollment = await db.execute(
            select(Enrollment).where(
                Enrollment.section_id == team.section_id,
                Enrollment.student_email == email,
            )
        )
        if enrollment.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{email} is not enrolled in this section",
            )
        db.add(TeamMembership(team_id=team.id, student_email=email))
        members_added.append(email)

    await db.commit()
    return TeamResponse(
        id=team.id,
        section_id=team.section_id,
        presentation_type_id=team.presentation_type_id,
        name=team.name,
        members=members_added,
    )
