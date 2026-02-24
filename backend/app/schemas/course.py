from datetime import datetime

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    name: str = Field(max_length=200)
    term: str = Field(max_length=50)


class CourseResponse(BaseModel):
    id: str
    name: str
    term: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
