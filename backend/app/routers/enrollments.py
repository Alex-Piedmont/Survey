import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.user import User
from app.schemas.enrollment import EnrollRequest, EnrollResult, RoleUpdate, RosterEntry

router = APIRouter(prefix="/api/v1/sections", tags=["enrollments"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


async def _verify_instructor(db: AsyncSession, section_id: str, email: str) -> Section:
    """Verify the user is an instructor for the course that owns this section."""
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
            detail="Only instructors can manage enrollments",
        )
    return section


@router.post("/{section_id}/enroll", response_model=EnrollResult)
async def bulk_enroll(
    section_id: str,
    body: EnrollRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk enroll students by newline-delimited emails (FR-7)."""
    section = await _verify_instructor(db, section_id, current_user.email)

    raw_emails = [e.strip().lower() for e in body.emails.splitlines() if e.strip()]

    enrolled = []
    duplicates = []
    invalid = []

    # Get existing enrollments for this section
    existing = await db.execute(
        select(Enrollment.student_email).where(Enrollment.section_id == section_id)
    )
    existing_emails = {row[0] for row in existing.all()}

    seen = set()
    for email in raw_emails:
        if not EMAIL_REGEX.match(email):
            invalid.append(email)
            continue

        if email in seen or email in existing_emails:
            duplicates.append(email)
            continue

        seen.add(email)

        # Upsert user record
        user_result = await db.execute(select(User).where(User.email == email))
        if user_result.scalar_one_or_none() is None:
            db.add(User(email=email))

        db.add(Enrollment(section_id=section_id, student_email=email, role="student"))
        enrolled.append(email)

    await db.commit()
    return EnrollResult(enrolled=enrolled, duplicates=duplicates, invalid=invalid)


@router.get("/{section_id}/roster", response_model=list[RosterEntry])
async def get_roster(
    section_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get section roster. Instructor or TA only."""
    result = await db.execute(select(Section).where(Section.id == section_id))
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # Check instructor or TA role
    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == section.course_id,
            Enrollment.student_email == current_user.email,
            Enrollment.role.in_(["instructor", "ta"]),
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and TAs can view the roster",
        )

    enrollments = await db.execute(
        select(Enrollment.student_email, Enrollment.role).where(
            Enrollment.section_id == section_id
        )
    )
    return [RosterEntry(email=row[0], role=row[1]) for row in enrollments.all()]


@router.patch("/{section_id}/roster/{email}/role")
async def update_role(
    section_id: str,
    email: str,
    body: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote/demote a user's role in a section. Instructor only."""
    await _verify_instructor(db, section_id, current_user.email)

    result = await db.execute(
        select(Enrollment).where(
            Enrollment.section_id == section_id,
            Enrollment.student_email == email,
        )
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in this section",
        )

    enrollment.role = body.role
    await db.commit()
    return {"email": email, "role": body.role}


@router.post("/{section_id}/verify-student")
async def verify_student(
    section_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instructor manually verifies a student, granting them a session token (FR-2a).
    Fallback when OTP delivery fails."""
    await _verify_instructor(db, section_id, current_user.email)

    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email is required",
        )

    # Verify student is enrolled
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.section_id == section_id,
            Enrollment.student_email == email,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in this section",
        )

    # Ensure user record exists
    user_result = await db.execute(select(User).where(User.email == email))
    if user_result.scalar_one_or_none() is None:
        db.add(User(email=email))
        await db.commit()

    token = create_access_token(email)
    return {"access_token": token, "token_type": "bearer"}
