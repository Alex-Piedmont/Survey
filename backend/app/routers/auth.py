import random
import string
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_otp, verify_otp
from app.models.user import OTPCode, User
from app.schemas.auth import GoogleAuthRequest, OTPRequest, OTPVerify
from app.schemas.user import TokenResponse, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


async def _upsert_user(db: AsyncSession, email: str, **kwargs) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=email, **kwargs)
        db.add(user)
    else:
        for key, value in kwargs.items():
            if value is not None:
                setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google OAuth authorization code for a JWT."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": body.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": body.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange authorization code",
            )
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user info from Google",
            )
        userinfo = userinfo_resp.json()

    user = await _upsert_user(
        db,
        email=userinfo["email"],
        display_name=userinfo.get("name"),
        google_id=userinfo.get("id"),
    )
    token = create_access_token(
        user.email, is_admin=user.is_admin, is_instructor=user.is_instructor
    )
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(body: OTPRequest, db: AsyncSession = Depends(get_db)):
    """Generate a 6-digit OTP and store it. In production, this sends an email."""
    code = "".join(random.choices(string.digits, k=6))
    otp = OTPCode(
        email=body.email,
        hashed_code=hash_otp(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(otp)
    await db.commit()

    # TODO: Send email via SendGrid in production
    # For development, log the code
    return {"message": "OTP sent to email", "_dev_code": code}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp_endpoint(body: OTPVerify, db: AsyncSession = Depends(get_db)):
    """Verify an OTP code and return a JWT."""
    result = await db.execute(
        select(OTPCode)
        .where(
            OTPCode.email == body.email,
            OTPCode.used == False,
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
        .order_by(OTPCode.expires_at.desc())
        .limit(1)
    )
    otp_record = result.scalar_one_or_none()

    if otp_record is None or not verify_otp(body.code, otp_record.hashed_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    otp_record.used = True
    user = await _upsert_user(db, email=body.email)
    await db.commit()

    token = create_access_token(
        user.email, is_admin=user.is_admin, is_instructor=user.is_instructor
    )
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))
