from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.instructor_ta import InstructorTA
from app.models.section import Section
from app.models.session import Session
from app.models.submission import Submission
from app.models.user import User


async def get_dashboard_stats(db: AsyncSession) -> dict:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_instructors = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_instructor == True)  # noqa: E712
        )
    ).scalar_one()
    total_admins = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_admin == True)  # noqa: E712
        )
    ).scalar_one()
    total_courses = (await db.execute(select(func.count()).select_from(Course))).scalar_one()
    total_active_sessions = (
        await db.execute(
            select(func.count()).select_from(Session).where(Session.status == "open")
        )
    ).scalar_one()
    total_submissions = (
        await db.execute(select(func.count()).select_from(Submission))
    ).scalar_one()

    # Recent courses with stats
    courses_result = await db.execute(
        select(Course).order_by(Course.created_at.desc()).limit(10)
    )
    courses = courses_result.scalars().all()

    recent_courses = []
    for c in courses:
        section_count = (
            await db.execute(
                select(func.count()).select_from(Section).where(Section.course_id == c.id)
            )
        ).scalar_one()
        student_count = (
            await db.execute(
                select(func.count(distinct(Enrollment.student_email)))
                .join(Section, Enrollment.section_id == Section.id)
                .where(Section.course_id == c.id)
            )
        ).scalar_one()
        recent_courses.append(
            {
                "id": c.id,
                "name": c.name,
                "term": c.term,
                "instructor_email": c.created_by,
                "section_count": section_count,
                "student_count": student_count,
            }
        )

    return {
        "total_users": total_users,
        "total_instructors": total_instructors,
        "total_admins": total_admins,
        "total_courses": total_courses,
        "total_active_sessions": total_active_sessions,
        "total_submissions": total_submissions,
        "recent_courses": recent_courses,
    }


async def grant_instructor(db: AsyncSession, email: str) -> dict:
    """Grant instructor privileges. Create user if needed."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    created = False

    if user is None:
        user = User(email=email, is_instructor=True)
        db.add(user)
        created = True
    else:
        user.is_instructor = True

    await db.commit()
    await db.refresh(user)
    return {
        "email": user.email,
        "display_name": user.display_name,
        "is_instructor": user.is_instructor,
        "created": created,
    }


async def revoke_instructor(db: AsyncSession, email: str) -> None:
    """Revoke instructor privileges."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    user.is_instructor = False
    await db.commit()


async def assign_ta(
    db: AsyncSession, instructor_email: str, ta_email: str, admin_email: str
) -> int:
    """Assign a TA under an instructor. Auto-enroll in instructor's sections.
    Returns the number of sections enrolled into."""
    # Ensure TA user exists
    ta_result = await db.execute(select(User).where(User.email == ta_email))
    if ta_result.scalar_one_or_none() is None:
        db.add(User(email=ta_email))
        await db.flush()

    # Create InstructorTA record
    record = InstructorTA(
        instructor_email=instructor_email,
        ta_email=ta_email,
        created_by=admin_email,
    )
    db.add(record)
    await db.flush()

    # Auto-enroll TA in all instructor's course sections
    sections_result = await db.execute(
        select(Section)
        .join(Course, Section.course_id == Course.id)
        .where(Course.created_by == instructor_email)
    )
    sections = sections_result.scalars().all()

    enrolled_count = 0
    for section in sections:
        # Check if already enrolled
        existing = await db.execute(
            select(Enrollment).where(
                Enrollment.section_id == section.id,
                Enrollment.student_email == ta_email,
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                Enrollment(section_id=section.id, student_email=ta_email, role="ta")
            )
            enrolled_count += 1

    await db.commit()
    return enrolled_count


async def remove_ta(db: AsyncSession, instructor_email: str, ta_email: str) -> None:
    """Remove TA from instructor. Demote to student in instructor's sections."""
    # Delete InstructorTA record
    result = await db.execute(
        select(InstructorTA).where(
            InstructorTA.instructor_email == instructor_email,
            InstructorTA.ta_email == ta_email,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise ValueError("TA assignment not found")
    await db.delete(record)

    # Demote to student in instructor's sections
    sections_result = await db.execute(
        select(Section)
        .join(Course, Section.course_id == Course.id)
        .where(Course.created_by == instructor_email)
    )
    sections = sections_result.scalars().all()

    for section in sections:
        enroll_result = await db.execute(
            select(Enrollment).where(
                Enrollment.section_id == section.id,
                Enrollment.student_email == ta_email,
            )
        )
        enrollment = enroll_result.scalar_one_or_none()
        if enrollment and enrollment.role == "ta":
            enrollment.role = "student"

    await db.commit()
