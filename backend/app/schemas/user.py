from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    email: EmailStr
    display_name: str | None = None
    is_admin: bool = False
    is_instructor: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
