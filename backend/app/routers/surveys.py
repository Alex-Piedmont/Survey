from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.survey import PresentationType, Question, SurveyTemplate
from app.models.user import User
from app.schemas.survey import (
    PresentationTypeCreate,
    PresentationTypeResponse,
    QuestionResponse,
    TemplateResponse,
    TemplateUpdate,
)

router = APIRouter(tags=["surveys"])


async def _verify_course_instructor(db: AsyncSession, course_id: str, email: str):
    access = await db.execute(
        select(Enrollment)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == course_id,
            Enrollment.student_email == email,
            Enrollment.role == "instructor",
        )
        .limit(1)
    )
    if access.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can manage presentation types",
        )


@router.post(
    "/api/v1/courses/{course_id}/presentation-types",
    response_model=PresentationTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_presentation_type(
    course_id: str,
    body: PresentationTypeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a presentation type. Auto-creates a v1 template."""
    await _verify_course_instructor(db, course_id, current_user.email)

    ptype = PresentationType(course_id=course_id, name=body.name)
    db.add(ptype)
    await db.flush()

    # Auto-create a v1 template (empty, instructor will add questions)
    template = SurveyTemplate(presentation_type_id=ptype.id, version=1)
    db.add(template)

    await db.commit()
    await db.refresh(ptype)
    return ptype


@router.get(
    "/api/v1/courses/{course_id}/presentation-types",
    response_model=list[PresentationTypeResponse],
)
async def list_presentation_types(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List presentation types for a course."""
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

    result = await db.execute(
        select(PresentationType).where(PresentationType.course_id == course_id)
    )
    return result.scalars().all()


@router.get(
    "/api/v1/presentation-types/{ptype_id}/template",
    response_model=TemplateResponse,
)
async def get_template(
    ptype_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest template version for a presentation type."""
    result = await db.execute(
        select(SurveyTemplate)
        .options(selectinload(SurveyTemplate.questions))
        .where(SurveyTemplate.presentation_type_id == ptype_id)
        .order_by(SurveyTemplate.version.desc())
        .limit(1)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return TemplateResponse(
        id=template.id,
        presentation_type_id=template.presentation_type_id,
        version=template.version,
        created_at=template.created_at,
        questions=[QuestionResponse.model_validate(q) for q in template.questions],
    )


@router.put(
    "/api/v1/presentation-types/{ptype_id}/template",
    response_model=TemplateResponse,
)
async def update_template(
    ptype_id: str,
    body: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update template by creating a new version (FR-12). Does not affect existing sessions."""
    # Get presentation type and verify instructor access
    ptype = await db.execute(
        select(PresentationType).where(PresentationType.id == ptype_id)
    )
    ptype = ptype.scalar_one_or_none()
    if ptype is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Presentation type not found"
        )

    await _verify_course_instructor(db, ptype.course_id, current_user.email)

    # Get current max version
    result = await db.execute(
        select(SurveyTemplate.version)
        .where(SurveyTemplate.presentation_type_id == ptype_id)
        .order_by(SurveyTemplate.version.desc())
        .limit(1)
    )
    current_version = result.scalar_one_or_none() or 0

    # Create new template version
    new_template = SurveyTemplate(
        presentation_type_id=ptype_id, version=current_version + 1
    )
    db.add(new_template)
    await db.flush()

    # Add questions to the new template
    questions = []
    for q_data in body.questions:
        question = Question(
            template_id=new_template.id,
            question_text=q_data.question_text,
            question_type=q_data.question_type,
            category=q_data.category,
            options=q_data.options,
            is_required=q_data.is_required,
            sort_order=q_data.sort_order,
            is_active=q_data.is_active,
        )
        db.add(question)
        questions.append(question)

    await db.commit()
    await db.refresh(new_template)

    # Refresh questions to get their IDs
    for q in questions:
        await db.refresh(q)

    return TemplateResponse(
        id=new_template.id,
        presentation_type_id=new_template.presentation_type_id,
        version=new_template.version,
        created_at=new_template.created_at,
        questions=[QuestionResponse.model_validate(q) for q in questions],
    )
