from datetime import datetime

from pydantic import BaseModel, Field


class QuestionSchema(BaseModel):
    question_text: str = Field(max_length=500)
    question_type: str = Field(pattern="^(likert_5|likert_7|free_text|multiple_choice)$")
    category: str = Field(pattern="^(audience|peer|instructor)$")
    options: list[str] | None = None
    is_required: bool = True
    sort_order: int
    is_active: bool = True


class QuestionResponse(QuestionSchema):
    id: str

    model_config = {"from_attributes": True}


class PresentationTypeCreate(BaseModel):
    name: str = Field(max_length=200)


class PresentationTypeResponse(BaseModel):
    id: str
    course_id: str
    name: str

    model_config = {"from_attributes": True}


class TemplateUpdate(BaseModel):
    questions: list[QuestionSchema]


class TemplateResponse(BaseModel):
    id: str
    presentation_type_id: str
    version: int
    created_at: datetime
    questions: list[QuestionResponse]

    model_config = {"from_attributes": True}
