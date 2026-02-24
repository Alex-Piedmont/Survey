from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.user import User
from app.schemas.course import CourseCreate, CourseResponse
from app.schemas.section import SectionCreate, SectionResponse

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a course. The creator is auto-enrolled as instructor (FR-4)."""
    course = Course(name=body.name, term=body.term, created_by=current_user.email)
    db.add(course)
    await db.flush()

    # Create a default section and enroll creator as instructor
    default_section = Section(course_id=course.id, name="Default")
    db.add(default_section)
    await db.flush()

    enrollment = Enrollment(
        section_id=default_section.id,
        student_email=current_user.email,
        role="instructor",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List courses the authenticated user is enrolled in."""
    result = await db.execute(
        select(Course)
        .join(Section, Section.course_id == Course.id)
        .join(Enrollment, Enrollment.section_id == Section.id)
        .where(Enrollment.student_email == current_user.email)
        .distinct()
    )
    return result.scalars().all()


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get course details. User must be enrolled in the course."""
    # Verify user has access to this course
    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == course_id,
            Enrollment.student_email == current_user.email,
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course",
        )

    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


@router.post(
    "/{course_id}/sections",
    response_model=SectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_section(
    course_id: str,
    body: SectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a section under a course. Instructor only."""
    # Verify instructor role
    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == course_id,
            Enrollment.student_email == current_user.email,
            Enrollment.role == "instructor",
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can create sections",
        )

    # Check course exists
    course = await db.execute(select(Course).where(Course.id == course_id))
    if course.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    section = Section(course_id=course_id, name=body.name)
    db.add(section)

    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Section '{body.name}' already exists in this course",
        )

    # Auto-enroll the instructor in the new section
    enrollment = Enrollment(
        section_id=section.id,
        student_email=current_user.email,
        role="instructor",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(section)
    return section


@router.get("/{course_id}/sections", response_model=list[SectionResponse])
async def list_sections(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sections for a course. User must be enrolled."""
    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == course_id,
            Enrollment.student_email == current_user.email,
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course",
        )

    result = await db.execute(select(Section).where(Section.course_id == course_id))
    return result.scalars().all()
