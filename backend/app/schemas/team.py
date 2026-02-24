from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(max_length=200)
    presentation_type_id: str
    member_emails: list[str] = []


class TeamResponse(BaseModel):
    id: str
    section_id: str
    presentation_type_id: str
    name: str
    members: list[str] = []

    model_config = {"from_attributes": True}


class TeamMemberUpdate(BaseModel):
    member_emails: list[str]
