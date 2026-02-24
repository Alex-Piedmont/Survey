import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


async def _setup_full_session(client: AsyncClient, auth_headers: dict) -> dict:
    """Create full setup: course, section, enrolled students, ptype with template,
    two teams, and a session. Returns all IDs."""
    # Course
    resp = await client.post(
        "/api/v1/courses",
        json={"name": "MGMT 481", "term": "Spring 2026"},
        headers=auth_headers,
    )
    course_id = resp.json()["id"]

    # Section
    resp = await client.post(
        f"/api/v1/courses/{course_id}/sections",
        json={"name": "Section A"},
        headers=auth_headers,
    )
    section_id = resp.json()["id"]

    # Enroll students
    await client.post(
        f"/api/v1/sections/{section_id}/enroll",
        json={
            "emails": "alice@uni.edu\nbob@uni.edu\ncharlie@uni.edu\ndave@uni.edu\neve@uni.edu"
        },
        headers=auth_headers,
    )

    # Presentation type + template
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
                {
                    "question_text": "Comments",
                    "question_type": "free_text",
                    "category": "audience",
                    "is_required": False,
                    "sort_order": 2,
                },
                {
                    "question_text": "Contribution",
                    "question_type": "likert_5",
                    "category": "peer",
                    "sort_order": 3,
                },
            ]
        },
        headers=auth_headers,
    )

    # Team Alpha: alice, bob
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

    # Team Beta: charlie, dave
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

    # Create session with both teams presenting
    resp = await client.post(
        "/api/v1/sessions",
        json={
            "section_id": section_id,
            "presentation_type_id": ptype_id,
            "presenting_team_ids": [team_alpha_id, team_beta_id],
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
        "team_beta_id": team_beta_id,
        "session_id": session_id,
    }


def _student_headers(email: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(email)}"}


class TestAudienceFeedback:
    async def test_audience_submits_for_one_team(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Per-page save: audience submits for one team at a time."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")  # eve is audience

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 4, "q2": "Great presentation"},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "audience"
        assert data["target_team_id"] == ids["team_alpha_id"]
        assert data["version"] == 1
        assert data["is_late"] is False
        assert data["penalty_pct"] == 0

    async def test_audience_submits_for_all_teams(
        self, client: AsyncClient, auth_headers: dict
    ):
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        # Submit for Team Alpha
        resp1 = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 4},
            },
            headers=headers,
        )
        assert resp1.status_code == 201

        # Submit for Team Beta
        resp2 = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_beta_id"],
                "feedback_type": "audience",
                "responses": {"q1": 3},
            },
            headers=headers,
        )
        assert resp2.status_code == 201

        # Verify both submissions exist
        resp = await client.get(
            f"/api/v1/s/{ids['session_id']}/submissions",
            headers=headers,
        )
        assert len(resp.json()) == 2

    async def test_presenter_cannot_rate_own_team(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Alice is on Team Alpha; can't submit audience feedback for Team Alpha."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("alice@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 5},
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert "own team" in resp.json()["detail"]

    async def test_presenter_can_rate_other_team(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Alice is on Team Alpha; can submit audience feedback for Team Beta."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("alice@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_beta_id"],
                "feedback_type": "audience",
                "responses": {"q1": 4},
            },
            headers=headers,
        )
        assert resp.status_code == 201


class TestPeerFeedback:
    async def test_presenter_submits_peer_feedback(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Alice submits peer feedback for Bob (both on Team Alpha)."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("alice@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_student_email": "bob@uni.edu",
                "feedback_type": "peer",
                "responses": {"contribution": 4},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "peer"
        assert data["target_student_email"] == "bob@uni.edu"
        assert data["target_team_id"] == ids["team_alpha_id"]

    async def test_self_evaluation_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("alice@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_student_email": "alice@uni.edu",
                "feedback_type": "peer",
                "responses": {"contribution": 5},
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert "Self-evaluation" in resp.json()["detail"]

    async def test_audience_cannot_submit_peer(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Eve is audience; cannot submit peer feedback."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_student_email": "alice@uni.edu",
                "feedback_type": "peer",
                "responses": {"contribution": 3},
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert "Only presenters" in resp.json()["detail"]

    async def test_peer_feedback_wrong_team(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Alice (Team Alpha) can't give peer feedback to Charlie (Team Beta)."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("alice@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_student_email": "charlie@uni.edu",
                "feedback_type": "peer",
                "responses": {"contribution": 3},
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert "not on your team" in resp.json()["detail"]


class TestRevisions:
    async def test_revision_creates_new_version(
        self, client: AsyncClient, auth_headers: dict
    ):
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        # Version 1
        resp1 = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 3},
            },
            headers=headers,
        )
        assert resp1.json()["version"] == 1

        # Version 2 (revision)
        resp2 = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 4, "q2": "Updated comment"},
            },
            headers=headers,
        )
        assert resp2.json()["version"] == 2

    async def test_get_submissions_returns_latest_only(
        self, client: AsyncClient, auth_headers: dict
    ):
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        # Submit v1 and v2 for same target
        await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 3},
            },
            headers=headers,
        )
        await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 5},
            },
            headers=headers,
        )

        resp = await client.get(
            f"/api/v1/s/{ids['session_id']}/submissions",
            headers=headers,
        )
        subs = resp.json()
        assert len(subs) == 1  # Latest version only
        assert subs[0]["version"] == 2
        assert subs[0]["responses"]["q1"] == 5


class TestEnrollmentValidation:
    async def test_unenrolled_student_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        ids = await _setup_full_session(client, auth_headers)

        # Create a user not enrolled in the section
        otp_resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "outsider@uni.edu"},
        )
        code = otp_resp.json()["_dev_code"]
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "outsider@uni.edu", "code": code},
        )
        headers = _student_headers("outsider@uni.edu")

        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 5},
            },
            headers=headers,
        )
        assert resp.status_code == 403
        assert "not enrolled" in resp.json()["detail"]


class TestMySubmissions:
    async def test_get_all_submissions(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_alpha_id"],
                "feedback_type": "audience",
                "responses": {"q1": 4},
            },
            headers=headers,
        )

        resp = await client.get("/api/v1/me/submissions", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["student_email"] == "eve@uni.edu"
