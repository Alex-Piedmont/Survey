from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.instructor_ta import InstructorTA
from app.models.presentation_grade import PresentationGrade
from app.models.section import Section
from app.models.session import Session
from app.models.submission import Submission
from app.models.survey import PresentationType, Question, SurveyTemplate
from app.models.user import User
from app.schemas.admin import (
    AdminCourseItem,
    AdminToggle,
    AdminUserDetail,
    AdminUserItem,
    DashboardStats,
    InstructorCreate,
    InstructorCreateResponse,
    InstructorDetail,
    InstructorItem,
    TAAssign,
    TAAssignResponse,
    TAItem,
)
from app.services.admin import (
    assign_ta,
    get_dashboard_stats,
    get_instructor_detail,
    grant_instructor,
    remove_ta,
    revoke_instructor,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_stats(db)


@router.get("/users", response_model=list[AdminUserItem])
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )
    users = result.scalars().all()

    items = []
    for u in users:
        course_count = (
            await db.execute(
                select(func.count()).select_from(Course).where(Course.created_by == u.email)
            )
        ).scalar_one()
        items.append(
            AdminUserItem(
                email=u.email,
                display_name=u.display_name,
                is_admin=u.is_admin,
                is_instructor=u.is_instructor,
                course_count=course_count,
                created_at=u.created_at,
            )
        )
    return items


@router.get("/users/{email}", response_model=AdminUserDetail)
async def get_user_detail(
    email: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    enrollments_result = await db.execute(
        select(
            Enrollment.section_id,
            Enrollment.role,
            Section.name.label("section_name"),
            Course.name.label("course_name"),
            Course.id.label("course_id"),
        )
        .join(Section, Enrollment.section_id == Section.id)
        .join(Course, Section.course_id == Course.id)
        .where(Enrollment.student_email == email)
    )
    enrollments = [
        {
            "section_id": r.section_id,
            "section_name": r.section_name,
            "course_id": r.course_id,
            "course_name": r.course_name,
            "role": r.role,
        }
        for r in enrollments_result.all()
    ]

    return AdminUserDetail(
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        is_instructor=user.is_instructor,
        created_at=user.created_at,
        enrollments=enrollments,
    )


@router.patch("/users/{email}/admin")
async def toggle_admin(
    email: str,
    body: AdminToggle,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not body.enabled:
        # Prevent removing the last admin
        admin_count = (
            await db.execute(
                select(func.count()).select_from(User).where(User.is_admin == True)  # noqa: E712
            )
        ).scalar_one()
        if admin_count <= 1 and user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin",
            )

    user.is_admin = body.enabled
    await db.commit()
    return {"email": email, "is_admin": body.enabled}


@router.get("/instructors", response_model=list[InstructorItem])
async def list_instructors(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.is_instructor == True).order_by(User.email)  # noqa: E712
    )
    instructors = result.scalars().all()

    items = []
    for i in instructors:
        course_count = (
            await db.execute(
                select(func.count()).select_from(Course).where(Course.created_by == i.email)
            )
        ).scalar_one()
        ta_count = (
            await db.execute(
                select(func.count())
                .select_from(InstructorTA)
                .where(InstructorTA.instructor_email == i.email)
            )
        ).scalar_one()
        items.append(
            InstructorItem(
                email=i.email,
                display_name=i.display_name,
                course_count=course_count,
                ta_count=ta_count,
            )
        )
    return items


@router.post(
    "/instructors",
    response_model=InstructorCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_instructor(
    body: InstructorCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Check if already an instructor
    existing = await db.execute(select(User).where(User.email == body.email))
    user = existing.scalar_one_or_none()
    if user and user.is_instructor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user already has instructor privileges",
        )

    result = await grant_instructor(db, body.email)
    return InstructorCreateResponse(**result)


@router.delete("/instructors/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instructor(
    email: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await revoke_instructor(db, email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/instructors/{email}/courses", response_model=InstructorDetail)
async def get_instructor_courses(
    email: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_instructor_detail(db, email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/instructors/{email}/tas", response_model=list[TAItem])
async def list_tas(
    email: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InstructorTA).where(InstructorTA.instructor_email == email)
    )
    records = result.scalars().all()

    items = []
    for r in records:
        ta_user = await db.execute(select(User).where(User.email == r.ta_email))
        ta = ta_user.scalar_one_or_none()
        items.append(
            TAItem(
                ta_email=r.ta_email,
                display_name=ta.display_name if ta else None,
                created_at=r.created_at,
                created_by=r.created_by,
            )
        )
    return items


@router.post(
    "/instructors/{email}/tas",
    response_model=TAAssignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ta(
    email: str,
    body: TAAssign,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify instructor exists and is an instructor
    instructor = await db.execute(select(User).where(User.email == email))
    instructor_user = instructor.scalar_one_or_none()
    if instructor_user is None or not instructor_user.is_instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found",
        )

    # Check for duplicate
    existing = await db.execute(
        select(InstructorTA).where(
            InstructorTA.instructor_email == email,
            InstructorTA.ta_email == body.ta_email,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="TA is already assigned to this instructor",
        )

    sections_enrolled = await assign_ta(db, email, body.ta_email, admin.email)
    return TAAssignResponse(
        instructor_email=email,
        ta_email=body.ta_email,
        sections_enrolled=sections_enrolled,
    )


@router.delete(
    "/instructors/{email}/tas/{ta_email}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ta(
    email: str,
    ta_email: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await remove_ta(db, email, ta_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/courses", response_model=list[AdminCourseItem])
async def list_all_courses(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Course).order_by(Course.created_at.desc()).offset(offset).limit(per_page)
    )
    courses = result.scalars().all()

    items = []
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
        items.append(
            AdminCourseItem(
                id=c.id,
                name=c.name,
                term=c.term,
                instructor_email=c.created_by,
                section_count=section_count,
                student_count=student_count,
            )
        )
    return items


@router.get("/courses/{course_id}", response_model=AdminCourseItem)
async def get_course_detail(
    course_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    section_count = (
        await db.execute(
            select(func.count()).select_from(Section).where(Section.course_id == course_id)
        )
    ).scalar_one()
    student_count = (
        await db.execute(
            select(func.count(distinct(Enrollment.student_email)))
            .join(Section, Enrollment.section_id == Section.id)
            .where(Section.course_id == course_id)
        )
    ).scalar_one()

    return AdminCourseItem(
        id=course.id,
        name=course.name,
        term=course.term,
        instructor_email=course.created_by,
        section_count=section_count,
        student_count=student_count,
    )


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a course and all related data (sections, enrollments, sessions, etc.)."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Delete related data in dependency order
    section_ids_q = select(Section.id).where(Section.course_id == course_id)
    session_ids_q = select(Session.id).where(Session.section_id.in_(section_ids_q))
    ptype_ids_q = select(PresentationType.id).where(PresentationType.course_id == course_id)
    template_ids_q = select(SurveyTemplate.id).where(SurveyTemplate.presentation_type_id.in_(ptype_ids_q))

    # Session children
    await db.execute(Submission.__table__.delete().where(Submission.session_id.in_(session_ids_q)))
    await db.execute(PresentationGrade.__table__.delete().where(PresentationGrade.session_id.in_(session_ids_q)))
    from app.models.session import SessionTeam
    await db.execute(SessionTeam.__table__.delete().where(SessionTeam.session_id.in_(session_ids_q)))
    await db.execute(Session.__table__.delete().where(Session.id.in_(session_ids_q)))

    # Section children
    await db.execute(Enrollment.__table__.delete().where(Enrollment.section_id.in_(section_ids_q)))
    await db.execute(Section.__table__.delete().where(Section.course_id == course_id))

    # Survey template children
    await db.execute(Question.__table__.delete().where(Question.template_id.in_(template_ids_q)))
    await db.execute(SurveyTemplate.__table__.delete().where(SurveyTemplate.presentation_type_id.in_(ptype_ids_q)))
    await db.execute(PresentationType.__table__.delete().where(PresentationType.course_id == course_id))

    # Course itself
    await db.execute(Course.__table__.delete().where(Course.id == course_id))
    await db.commit()


@router.post("/users/{email}/reset-password", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def reset_password(
    email: str,
    admin: User = Depends(require_admin),
):
    return {"detail": "Password reset not yet implemented (password auth not available)"}
