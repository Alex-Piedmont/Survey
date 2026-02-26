import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, verify_access_token


class TestJWT:
    def test_create_and_verify_token(self):
        token = create_access_token("test@example.com")
        payload = verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "test@example.com"
        assert payload["is_admin"] is False
        assert payload["is_instructor"] is False

    def test_create_token_with_admin_flags(self):
        token = create_access_token("admin@example.com", is_admin=True, is_instructor=True)
        payload = verify_access_token(token)
        assert payload is not None
        assert payload["is_admin"] is True
        assert payload["is_instructor"] is True

    def test_invalid_token_returns_none(self):
        assert verify_access_token("garbage.token.here") is None

    def test_empty_token_returns_none(self):
        assert verify_access_token("") is None


class TestOTPFlow:
    async def test_request_otp(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "student@university.edu"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "message" in data
        assert "_dev_code" in data  # Dev mode returns the code

    async def test_verify_otp(self, client: AsyncClient):
        # Request OTP
        resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "student@university.edu"},
        )
        code = resp.json()["_dev_code"]

        # Verify OTP
        resp = await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "student@university.edu", "code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "student@university.edu"

    async def test_verify_wrong_otp(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "student@university.edu"},
        )
        resp = await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "student@university.edu", "code": "000000"},
        )
        assert resp.status_code == 401

    async def test_otp_cannot_be_reused(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "student@university.edu"},
        )
        code = resp.json()["_dev_code"]

        # First verify succeeds
        resp = await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "student@university.edu", "code": code},
        )
        assert resp.status_code == 200

        # Second verify fails (OTP marked as used)
        resp = await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "student@university.edu", "code": code},
        )
        assert resp.status_code == 401


class TestProtectedEndpoints:
    async def test_no_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/courses")
        assert resp.status_code in (401, 403)

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/courses",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert resp.status_code == 401
