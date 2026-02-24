from pydantic import BaseModel, EmailStr, Field


class EnrollRequest(BaseModel):
    emails: str = Field(description="Newline-delimited list of student emails")


class EnrollResult(BaseModel):
    enrolled: list[str]
    duplicates: list[str]
    invalid: list[str]


class RosterEntry(BaseModel):
    email: str
    role: str

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    role: str = Field(pattern="^(student|ta)$")
