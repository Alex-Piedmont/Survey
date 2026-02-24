import pytest
from httpx import AsyncClient


async def _create_course_and_section(client: AsyncClient, auth_headers: dict) -> tuple[str, str]:
    """Helper: create a course and an additional section, return (course_id, section_id)."""
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
    section_id = resp.json()["id"]
    return course_id, section_id


class TestBulkEnroll:
    async def test_enroll_students(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "alice@uni.edu\nbob@uni.edu\ncharlie@uni.edu"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["enrolled"]) == 3
        assert len(data["duplicates"]) == 0
        assert len(data["invalid"]) == 0

    async def test_enroll_duplicate_emails(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        # First enrollment
        await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "alice@uni.edu\nbob@uni.edu"},
            headers=auth_headers,
        )

        # Second enrollment with overlap
        resp = await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "alice@uni.edu\ndave@uni.edu"},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["enrolled"] == ["dave@uni.edu"]
        assert data["duplicates"] == ["alice@uni.edu"]

    async def test_enroll_duplicates_within_batch(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "alice@uni.edu\nalice@uni.edu"},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["enrolled"] == ["alice@uni.edu"]
        assert data["duplicates"] == ["alice@uni.edu"]

    async def test_enroll_invalid_emails(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "valid@uni.edu\nnot-an-email\n@bad.com"},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["enrolled"] == ["valid@uni.edu"]
        assert len(data["invalid"]) == 2

    async def test_enroll_normalizes_case(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "Alice@Uni.EDU"},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["enrolled"] == ["alice@uni.edu"]

    async def test_enroll_handles_blank_lines(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "alice@uni.edu\n\n\nbob@uni.edu\n"},
            headers=auth_headers,
        )
        data = resp.json()
        assert len(data["enrolled"]) == 2


class TestRoster:
    async def test_get_roster(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "alice@uni.edu\nbob@uni.edu"},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/sections/{section_id}/roster",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        roster = resp.json()
        emails = {entry["email"] for entry in roster}
        assert "alice@uni.edu" in emails
        assert "bob@uni.edu" in emails

    async def test_roster_requires_instructor_or_ta(self, client: AsyncClient, auth_headers: dict):
        from app.core.security import create_access_token

        _, section_id = await _create_course_and_section(client, auth_headers)

        # Enroll student (this also creates the user record)
        await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "student@uni.edu"},
            headers=auth_headers,
        )

        student_headers = {
            "Authorization": f"Bearer {create_access_token('student@uni.edu')}"
        }
        resp = await client.get(
            f"/api/v1/sections/{section_id}/roster",
            headers=student_headers,
        )
        assert resp.status_code == 403


class TestRoleUpdate:
    async def test_promote_to_ta(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "ta@uni.edu"},
            headers=auth_headers,
        )

        resp = await client.patch(
            f"/api/v1/sections/{section_id}/roster/ta@uni.edu/role",
            json={"role": "ta"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "ta"

    async def test_invalid_role_rejected(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "student@uni.edu"},
            headers=auth_headers,
        )

        resp = await client.patch(
            f"/api/v1/sections/{section_id}/roster/student@uni.edu/role",
            json={"role": "instructor"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_promote_nonexistent_student(self, client: AsyncClient, auth_headers: dict):
        _, section_id = await _create_course_and_section(client, auth_headers)

        resp = await client.patch(
            f"/api/v1/sections/{section_id}/roster/nobody@uni.edu/role",
            json={"role": "ta"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
