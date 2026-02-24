from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    email: EmailStr
    display_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
