"""Tests for Phase 6: student role detection, instructor manual verify,
default templates, and /me/submissions latest-only."""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


async def _setup_full_session(client: AsyncClient, auth_headers: dict) -> dict:
    """Create full setup with course, section, enrolled students, teams, and session."""
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

    await client.post(
        f"/api/v1/sections/{section_id}/enroll",
        json={
            "emails": "alice@uni.edu\nbob@uni.edu\neve@uni.edu"
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/courses/{course_id}/presentation-types",
        json={"name": "Debates"},
        headers=auth_headers,
    )
    ptype_id = resp.json()["id"]

    await client.put(
        f"/api/v1/presentation-types/{ptype_id}/template",
        json={
            "questions": [
                {
                    "question_text": "Content clarity",
                    "question_type": "likert_5",
                    "category": "audience",
                    "sort_order": 1,
                },
            ]
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/sections/{section_id}/teams",
        json={
            "name": "Team Alpha",
            "presentation_type_id": ptype_id,
            "member_emails": ["alice@uni.edu", "bob@uni.edu"],
        },
        headers=auth_headers,
    )
    team_alpha_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/sessions",
        json={
            "section_id": section_id,
            "presentation_type_id": ptype_id,
            "presenting_team_ids": [team_alpha_id],
            "session_date": "2026-12-15",
        },
        headers=auth_headers,
    )
    session_id = resp.json()["id"]

    return {
        "course_id": course_id,
        "section_id": section_id,
        "ptype_id": ptype_id,
        "team_alpha_id": team_alpha_id,
        "session_id": session_id,
    }


def _student_headers(email: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(email)}"}


class TestStudentRoleDetection:
    async def test_no_auth_returns_audience(self, client: AsyncClient, auth_headers: dict):
        """Without auth, student_role defaults to 'audience'."""
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.get(f"/api/v1/s/{ids['session_id']}")
        assert resp.status_code == 200
        assert resp.json()["student_role"] == "audience"
        assert resp.json()["student_team_id"] is None

    async def test_presenter_detected(self, client: AsyncClient, auth_headers: dict):
        """Alice is on Team Alpha — should be detected as presenter."""
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.get(
            f"/api/v1/s/{ids['session_id']}",
            headers=_student_headers("alice@uni.edu"),
        )
        assert resp.status_code == 200
        assert resp.json()["student_role"] == "presenter"
        assert resp.json()["student_team_id"] == ids["team_alpha_id"]

    async def test_audience_detected(self, client: AsyncClient, auth_headers: dict):
        """Eve is not on any team — should be detected as audience."""
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.get(
            f"/api/v1/s/{ids['session_id']}",
            headers=_student_headers("eve@uni.edu"),
        )
        assert resp.status_code == 200
        assert resp.json()["student_role"] == "audience"
        assert resp.json()["student_team_id"] is None


class TestInstructorManualVerify:
    async def test_verify_enrolled_student(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{ids['section_id']}/verify-student",
            json={"email": "alice@uni.edu"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # The token should work for submitting feedback
        token_headers = {"Authorization": f"Bearer {data['access_token']}"}
        resp = await client.get(
            f"/api/v1/s/{ids['session_id']}",
            headers=token_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["student_role"] == "presenter"

    async def test_verify_unenrolled_student_rejected(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{ids['section_id']}/verify-student",
            json={"email": "nobody@uni.edu"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_verify_requires_instructor(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{ids['section_id']}/verify-student",
            json={"email": "alice@uni.edu"},
            headers=_student_headers("eve@uni.edu"),
        )
        assert resp.status_code == 403


class TestDefaultTemplates:
    async def test_seed_defaults(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "Template Course", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/courses/{course_id}/seed-defaults",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["created"]) == 3
        assert "Strategic Headlines" in data["created"]
        assert "Learning Team Debates" in data["created"]
        assert "Class Strategy Project" in data["created"]

    async def test_seed_idempotent(self, client: AsyncClient, auth_headers: dict):
        """Seeding twice should not duplicate."""
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "Idempotent Course", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        await client.post(
            f"/api/v1/courses/{course_id}/seed-defaults",
            headers=auth_headers,
        )
        resp = await client.post(
            f"/api/v1/courses/{course_id}/seed-defaults",
            headers=auth_headers,
        )
        assert resp.json()["created"] == []

    async def test_seeded_template_has_questions(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "Questions Course", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]

        await client.post(
            f"/api/v1/courses/{course_id}/seed-defaults",
            headers=auth_headers,
        )

        # List presentation types
        resp = await client.get(
            f"/api/v1/courses/{course_id}/presentation-types",
            headers=auth_headers,
        )
        ptypes = resp.json()
        assert len(ptypes) == 3

        # Check one has questions
        ptype_id = ptypes[0]["id"]
        resp = await client.get(
            f"/api/v1/presentation-types/{ptype_id}/template",
            headers=auth_headers,
        )
        template = resp.json()
        assert len(template["questions"]) > 0
        # Should have both audience and peer questions
        categories = {q["category"] for q in template["questions"]}
        assert "audience" in categories
        assert "peer" in categories


class TestMySubmissionsLatestOnly:
    async def test_returns_latest_version_only(self, client: AsyncClient, auth_headers: dict):
        """GET /me/submissions should return only the latest version per target."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        # Get question IDs
        resp = await client.get(f"/api/v1/s/{ids['session_id']}")
        qid = resp.json()["questions"][0]["id"]

        # Submit v1
        await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {qid: 3},
            },
            headers=headers,
        )

        # Submit v2 (revision)
        await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {qid: 5},
            },
            headers=headers,
        )

        resp = await client.get("/api/v1/me/submissions", headers=headers)
        assert resp.status_code == 200
        subs = resp.json()
        assert len(subs) == 1  # Latest version only
        assert subs[0]["version"] == 2
        assert subs[0]["responses"][qid] == 5
