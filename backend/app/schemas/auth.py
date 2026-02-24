from pydantic import BaseModel, EmailStr


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    code: str
