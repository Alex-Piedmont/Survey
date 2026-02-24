import pytest
from httpx import AsyncClient


async def _setup_full(client: AsyncClient, auth_headers: dict) -> dict:
    """Create course, section, ptype, template, teams. Returns all IDs."""
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
        json={"emails": "alice@uni.edu\nbob@uni.edu\ncharlie@uni.edu\ndave@uni.edu"},
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/courses/{course_id}/presentation-types",
        json={"name": "Debates"},
        headers=auth_headers,
    )
    ptype_id = resp.json()["id"]

    # Add questions to the template
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
                {
                    "question_text": "Delivery",
                    "question_type": "likert_5",
                    "category": "audience",
                    "sort_order": 2,
                },
                {
                    "question_text": "Comments",
                    "question_type": "free_text",
                    "category": "audience",
                    "is_required": False,
                    "sort_order": 3,
                },
                {
                    "question_text": "Contribution",
                    "question_type": "likert_5",
                    "category": "peer",
                    "sort_order": 4,
                },
            ]
        },
        headers=auth_headers,
    )

    # Create two teams
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
        f"/api/v1/sections/{section_id}/teams",
        json={
            "name": "Team Beta",
            "presentation_type_id": ptype_id,
            "member_emails": ["charlie@uni.edu", "dave@uni.edu"],
        },
        headers=auth_headers,
    )
    team_beta_id = resp.json()["id"]

    return {
        "course_id": course_id,
        "section_id": section_id,
        "ptype_id": ptype_id,
        "team_alpha_id": team_alpha_id,
        "team_beta_id": team_beta_id,
    }


class TestCreateSession:
    async def test_create_session(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full(client, auth_headers)

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"], ids["team_beta_id"]],
                "session_date": "2026-02-23",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["section_id"] == ids["section_id"]
        assert data["status"] == "open"
        assert len(data["presenting_team_ids"]) == 2
        assert data["template_snapshot_id"] is not None

    async def test_create_session_default_deadline(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full(client, auth_headers)

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"]],
                "session_date": "2026-02-23",
            },
            headers=auth_headers,
        )
        data = resp.json()
        # Default deadline: 2026-02-24 00:29:00 UTC (23:59 + 30 min)
        assert "2026-02-24" in data["deadline"]

    async def test_create_session_custom_deadline(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full(client, auth_headers)

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"]],
                "session_date": "2026-02-23",
                "deadline": "2026-02-23T18:00:00Z",
            },
            headers=auth_headers,
        )
        data = resp.json()
        assert "18:00" in data["deadline"]


class TestGetSession:
    async def test_get_session(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full(client, auth_headers)

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"], ids["team_beta_id"]],
                "session_date": "2026-02-23",
            },
            headers=auth_headers,
        )
        session_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id
        assert len(resp.json()["presenting_team_ids"]) == 2


class TestQRCode:
    async def test_get_qr_code(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full(client, auth_headers)

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"]],
                "session_date": "2026-02-23",
            },
            headers=auth_headers,
        )
        session_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/sessions/{session_id}/qr",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["qr_url"].endswith(f"/s/{session_id}")
        assert len(data["qr_base64"]) > 100  # Non-trivial base64 data


class TestTemplateSnapshot:
    async def test_snapshot_isolates_from_edits(self, client: AsyncClient, auth_headers: dict):
        """FR-12: Template edits after session creation don't affect the session."""
        ids = await _setup_full(client, auth_headers)

        # Create session (snapshots current template with 4 questions)
        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"]],
                "session_date": "2026-02-23",
            },
            headers=auth_headers,
        )
        session_id = resp.json()["id"]

        # Edit the template (add a 5th question)
        await client.put(
            f"/api/v1/presentation-types/{ids['ptype_id']}/template",
            json={
                "questions": [
                    {
                        "question_text": "New question",
                        "question_type": "likert_5",
                        "category": "audience",
                        "sort_order": 1,
                    },
                ]
            },
            headers=auth_headers,
        )

        # Student view should still show original 4 questions
        resp = await client.get(f"/api/v1/s/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["questions"]) == 4
        assert data["questions"][0]["question_text"] == "Content clarity"


class TestStudentSession:
    async def test_student_session_no_auth_required(
        self, client: AsyncClient, auth_headers: dict
    ):
        """GET /api/v1/s/{uuid} is public."""
        ids = await _setup_full(client, auth_headers)

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": ids["section_id"],
                "presentation_type_id": ids["ptype_id"],
                "presenting_team_ids": [ids["team_alpha_id"], ids["team_beta_id"]],
                "session_date": "2026-02-23",
            },
            headers=auth_headers,
        )
        session_id = resp.json()["id"]

        # No auth headers
        resp = await client.get(f"/api/v1/s/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["course_name"] == "MGMT 481"
        assert data["presentation_type_name"] == "Debates"
        assert len(data["presenting_teams"]) == 2
        assert len(data["questions"]) == 4

    async def test_student_session_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/s/nonexistent-uuid")
        assert resp.status_code == 404
