import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import User


@pytest.fixture
async def admin_user(db: AsyncSession):
    user = User(email="admin@test.com", display_name="Admin", is_admin=True, is_instructor=True)
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
def admin_headers(admin_user: User):
    token = create_access_token(admin_user.email, is_admin=True, is_instructor=True)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def regular_user(db: AsyncSession):
    user = User(email="regular@test.com", display_name="Regular")
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
def regular_headers(regular_user: User):
    token = create_access_token(regular_user.email)
    return {"Authorization": f"Bearer {token}"}


class TestAdminAuth:
    async def test_non_admin_gets_403(self, client: AsyncClient, regular_headers: dict):
        resp = await client.get("/api/v1/admin/dashboard", headers=regular_headers)
        assert resp.status_code == 403

    async def test_admin_gets_dashboard(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "total_courses" in data


class TestInstructorManagement:
    async def test_grant_instructor(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/admin/instructors",
            json={"email": "newinstructor@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newinstructor@test.com"
        assert data["is_instructor"] is True
        assert data["created"] is True

    async def test_grant_instructor_duplicate(
        self, client: AsyncClient, admin_headers: dict
    ):
        # First create
        await client.post(
            "/api/v1/admin/instructors",
            json={"email": "dup@test.com"},
            headers=admin_headers,
        )
        # Duplicate
        resp = await client.post(
            "/api/v1/admin/instructors",
            json={"email": "dup@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    async def test_revoke_instructor(self, client: AsyncClient, admin_headers: dict):
        await client.post(
            "/api/v1/admin/instructors",
            json={"email": "torevoike@test.com"},
            headers=admin_headers,
        )
        resp = await client.delete(
            "/api/v1/admin/instructors/torevoike@test.com",
            headers=admin_headers,
        )
        assert resp.status_code == 204

    async def test_list_instructors(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/v1/admin/instructors", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAdminToggle:
    async def test_last_admin_protection(
        self, client: AsyncClient, admin_headers: dict, admin_user: User
    ):
        resp = await client.patch(
            f"/api/v1/admin/users/{admin_user.email}/admin",
            json={"enabled": False},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "last admin" in resp.json()["detail"].lower()


class TestInstructorGate:
    async def test_non_instructor_cannot_create_course(
        self, client: AsyncClient, regular_headers: dict
    ):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "Test Course", "term": "Spring 2026"},
            headers=regular_headers,
        )
        assert resp.status_code == 403
        assert "instructor" in resp.json()["detail"].lower()


class TestTAManagement:
    async def test_assign_and_remove_ta(
        self, client: AsyncClient, admin_headers: dict
    ):
        # Create instructor first
        await client.post(
            "/api/v1/admin/instructors",
            json={"email": "prof@test.com"},
            headers=admin_headers,
        )
        # Assign TA
        resp = await client.post(
            "/api/v1/admin/instructors/prof@test.com/tas",
            json={"ta_email": "ta@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["ta_email"] == "ta@test.com"

        # List TAs
        resp = await client.get(
            "/api/v1/admin/instructors/prof@test.com/tas",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Remove TA
        resp = await client.delete(
            "/api/v1/admin/instructors/prof@test.com/tas/ta@test.com",
            headers=admin_headers,
        )
        assert resp.status_code == 204

    async def test_duplicate_ta_assignment(
        self, client: AsyncClient, admin_headers: dict
    ):
        await client.post(
            "/api/v1/admin/instructors",
            json={"email": "prof2@test.com"},
            headers=admin_headers,
        )
        await client.post(
            "/api/v1/admin/instructors/prof2@test.com/tas",
            json={"ta_email": "ta2@test.com"},
            headers=admin_headers,
        )
        resp = await client.post(
            "/api/v1/admin/instructors/prof2@test.com/tas",
            json={"ta_email": "ta2@test.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 409
