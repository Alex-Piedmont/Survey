import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.section import Section


class TestCreateCourse:
    async def test_create_course(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "MGMT 481"
        assert data["term"] == "Spring 2026"
        assert data["created_by"] == "instructor@university.edu"

    async def test_create_course_auto_enrolls_instructor(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        # Verify a default section was created
        sections = await db.execute(select(Section).where(Section.course_id == course_id))
        section = sections.scalar_one()
        assert section.name == "Default"

        # Verify instructor enrollment
        enrollments = await db.execute(
            select(Enrollment).where(
                Enrollment.section_id == section.id,
                Enrollment.student_email == "instructor@university.edu",
            )
        )
        enrollment = enrollments.scalar_one()
        assert enrollment.role == "instructor"

    async def test_create_course_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
        )
        assert resp.status_code in (401, 403)


class TestListCourses:
    async def test_list_courses(self, client: AsyncClient, auth_headers: dict):
        # Create two courses
        await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 580", "term": "Fall 2026"},
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/courses", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_courses_only_enrolled(self, client: AsyncClient, auth_headers: dict):
        """User only sees courses they're enrolled in."""
        from app.core.security import create_access_token

        # Create a course as instructor
        await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )

        # Create another user via OTP flow, then use their token
        otp_resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "other@uni.edu"},
        )
        code = otp_resp.json()["_dev_code"]
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "other@uni.edu", "code": code},
        )
        other_headers = {"Authorization": f"Bearer {create_access_token('other@uni.edu')}"}
        resp = await client.get("/api/v1/courses", headers=other_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0


class TestGetCourse:
    async def test_get_course(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/courses/{course_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "MGMT 481"

    async def test_get_course_not_enrolled(self, client: AsyncClient, auth_headers: dict):
        from app.core.security import create_access_token

        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        # Create another user via OTP
        otp_resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "other@uni.edu"},
        )
        code = otp_resp.json()["_dev_code"]
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "other@uni.edu", "code": code},
        )
        other_headers = {"Authorization": f"Bearer {create_access_token('other@uni.edu')}"}
        resp = await client.get(f"/api/v1/courses/{course_id}", headers=other_headers)
        assert resp.status_code == 403


class TestCreateSection:
    async def test_create_section(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/courses/{course_id}/sections",
            json={"name": "Section A"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Section A"

    async def test_duplicate_section_name(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        await client.post(
            f"/api/v1/courses/{course_id}/sections",
            json={"name": "Section A"},
            headers=auth_headers,
        )
        resp = await client.post(
            f"/api/v1/courses/{course_id}/sections",
            json={"name": "Section A"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_list_sections(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "MGMT 481", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        await client.post(
            f"/api/v1/courses/{course_id}/sections",
            json={"name": "Section A"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/courses/{course_id}/sections",
            json={"name": "Section B"},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/courses/{course_id}/sections",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Default section + 2 created sections
        assert len(resp.json()) == 3
