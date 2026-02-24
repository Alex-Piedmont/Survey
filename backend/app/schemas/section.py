from pydantic import BaseModel, Field


class SectionCreate(BaseModel):
    name: str = Field(max_length=100)


class SectionResponse(BaseModel):
    id: str
    course_id: str
    name: str

    model_config = {"from_attributes": True}
