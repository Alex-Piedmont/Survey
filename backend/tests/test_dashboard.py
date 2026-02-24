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

    # Create session
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


async def _get_question_ids(client: AsyncClient, session_id: str) -> dict[str, str]:
    """Get question IDs from the student session endpoint.
    Returns: {"likert": first_likert_id, "text": first_text_id, "peer": peer_likert_id}
    """
    resp = await client.get(f"/api/v1/s/{session_id}")
    questions = resp.json()["questions"]
    result = {}
    for q in questions:
        if q["question_type"].startswith("likert") and q["category"] == "audience" and "likert" not in result:
            result["likert"] = q["id"]
        elif q["question_type"] == "free_text" and "text" not in result:
            result["text"] = q["id"]
        elif q["question_type"].startswith("likert") and q["category"] == "peer" and "peer" not in result:
            result["peer"] = q["id"]
    return result


async def _submit_audience(
    client: AsyncClient, session_id: str, email: str, team_id: str,
    likert_qid: str, score: int, text_qid: str = "", text_value: str = ""
):
    """Helper to submit audience feedback using actual question IDs."""
    responses = {likert_qid: score}
    if text_qid and text_value:
        responses[text_qid] = text_value
    return await client.post(
        f"/api/v1/s/{session_id}/submit",
        json={
            "target_team_id": team_id,
            "feedback_type": "audience",
            "responses": responses,
        },
        headers=_student_headers(email),
    )


class TestDashboard:
    async def test_dashboard_empty(self, client: AsyncClient, auth_headers: dict):
        """Dashboard with no submissions yet."""
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/dashboard",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == ids["session_id"]
        assert data["enrolled_count"] == 5  # alice, bob, charlie, dave, eve
        assert data["submitted_count"] == 0
        assert len(data["not_submitted_emails"]) == 5
        assert len(data["team_averages"]) == 2

    async def test_dashboard_with_submissions(self, client: AsyncClient, auth_headers: dict):
        """Dashboard updates after submissions."""
        ids = await _setup_full_session(client, auth_headers)
        qids = await _get_question_ids(client, ids["session_id"])

        # Eve submits for Team Alpha
        await _submit_audience(client, ids["session_id"], "eve@uni.edu", ids["team_alpha_id"], qids["likert"], 4)

        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/dashboard",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["submitted_count"] == 1
        assert "eve@uni.edu" in data["submitted_emails"]
        assert "eve@uni.edu" not in data["not_submitted_emails"]

    async def test_dashboard_requires_instructor(self, client: AsyncClient, auth_headers: dict):
        """Students cannot access dashboard."""
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/dashboard",
            headers=headers,
        )
        assert resp.status_code == 403


class TestSummary:
    async def test_summary_with_scores(self, client: AsyncClient, auth_headers: dict):
        """Summary aggregates Likert scores correctly."""
        ids = await _setup_full_session(client, auth_headers)
        qids = await _get_question_ids(client, ids["session_id"])

        # Eve and Alice (can rate Beta) and Charlie (can rate Alpha) submit
        await _submit_audience(
            client, ids["session_id"], "eve@uni.edu", ids["team_alpha_id"],
            qids["likert"], 4, qids["text"], "Good job"
        )
        await _submit_audience(
            client, ids["session_id"], "eve@uni.edu", ids["team_beta_id"],
            qids["likert"], 3
        )
        # Charlie is on Team Beta, can rate Team Alpha
        await _submit_audience(
            client, ids["session_id"], "charlie@uni.edu", ids["team_alpha_id"],
            qids["likert"], 5, qids["text"], "Excellent"
        )

        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Check team scores exist
        assert len(data["team_scores"]) == 2

        # Check comments
        alpha_comments = next(
            tc for tc in data["team_comments"] if tc["team_id"] == ids["team_alpha_id"]
        )
        assert len(alpha_comments["comments"]) == 2  # "Good job" and "Excellent"

        # Check participation matrix
        assert len(data["participation_matrix"]) == 5

    async def test_summary_requires_instructor(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)
        headers = _student_headers("eve@uni.edu")

        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/summary",
            headers=headers,
        )
        assert resp.status_code == 403


class TestInstructorFeedback:
    async def test_submit_instructor_feedback(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/instructor-feedback",
            json={
                "target_team_id": ids["team_alpha_id"],
                "responses": {"q1": 5, "q2": "Outstanding presentation"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["version"] == 1

    async def test_instructor_feedback_versioning(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        # Version 1
        resp1 = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/instructor-feedback",
            json={
                "target_team_id": ids["team_alpha_id"],
                "responses": {"q1": 4},
            },
            headers=auth_headers,
        )
        assert resp1.json()["version"] == 1

        # Version 2
        resp2 = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/instructor-feedback",
            json={
                "target_team_id": ids["team_alpha_id"],
                "responses": {"q1": 5},
            },
            headers=auth_headers,
        )
        assert resp2.json()["version"] == 2

    async def test_instructor_feedback_invalid_team(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/instructor-feedback",
            json={
                "target_team_id": "nonexistent-team-id",
                "responses": {"q1": 5},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestPresentationGrade:
    async def test_assign_grade(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/teams/{ids['team_alpha_id']}/presentation-grade",
            json={"grade": "A", "comments": "Excellent work"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["grade"] == "A"
        assert data["comments"] == "Excellent work"
        assert data["team_id"] == ids["team_alpha_id"]

    async def test_update_grade(self, client: AsyncClient, auth_headers: dict):
        """Assigning grade again replaces the previous one."""
        ids = await _setup_full_session(client, auth_headers)

        await client.post(
            f"/api/v1/sessions/{ids['session_id']}/teams/{ids['team_alpha_id']}/presentation-grade",
            json={"grade": "B+"},
            headers=auth_headers,
        )
        resp = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/teams/{ids['team_alpha_id']}/presentation-grade",
            json={"grade": "A-"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["grade"] == "A-"

    async def test_grade_invalid_team(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sessions/{ids['session_id']}/teams/fake-id/presentation-grade",
            json={"grade": "A"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_grade_in_summary(self, client: AsyncClient, auth_headers: dict):
        """Grades appear in the summary response."""
        ids = await _setup_full_session(client, auth_headers)

        await client.post(
            f"/api/v1/sessions/{ids['session_id']}/teams/{ids['team_alpha_id']}/presentation-grade",
            json={"grade": "A"},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/summary",
            headers=auth_headers,
        )
        grades = resp.json()["presentation_grades"]
        assert len(grades) == 1
        assert grades[0]["grade"] == "A"


class TestWithholdComment:
    async def test_withhold_toggle(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)
        qids = await _get_question_ids(client, ids["session_id"])

        # Submit feedback with a comment
        resp = await _submit_audience(
            client, ids["session_id"], "eve@uni.edu", ids["team_alpha_id"],
            qids["likert"], 4, qids["text"], "Needs work"
        )
        submission_id = resp.json()["id"]

        # Withhold it
        resp = await client.put(
            f"/api/v1/sessions/{ids['session_id']}/comments/{submission_id}/withhold",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["withheld"] is True

        # Toggle back
        resp = await client.put(
            f"/api/v1/sessions/{ids['session_id']}/comments/{submission_id}/withhold",
            headers=auth_headers,
        )
        assert resp.json()["withheld"] is False

    async def test_withheld_in_summary(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)
        qids = await _get_question_ids(client, ids["session_id"])

        resp = await _submit_audience(
            client, ids["session_id"], "eve@uni.edu", ids["team_alpha_id"],
            qids["likert"], 4, qids["text"], "Secret comment"
        )
        submission_id = resp.json()["id"]

        # Withhold
        await client.put(
            f"/api/v1/sessions/{ids['session_id']}/comments/{submission_id}/withhold",
            headers=auth_headers,
        )

        # Check summary
        resp = await client.get(
            f"/api/v1/sessions/{ids['session_id']}/summary",
            headers=auth_headers,
        )
        alpha_comments = next(
            tc for tc in resp.json()["team_comments"] if tc["team_id"] == ids["team_alpha_id"]
        )
        assert any(c["withheld"] is True for c in alpha_comments["comments"])


class TestSessionList:
    async def test_list_sessions(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        resp = await client.get(
            f"/api/v1/sections/{ids['section_id']}/sessions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["id"] == ids["session_id"]
        assert sessions[0]["presenting_team_count"] == 2
        assert sessions[0]["submission_count"] == 0

    async def test_list_sessions_with_submissions(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)
        qids = await _get_question_ids(client, ids["session_id"])

        await _submit_audience(client, ids["session_id"], "eve@uni.edu", ids["team_alpha_id"], qids["likert"], 4)

        resp = await client.get(
            f"/api/v1/sections/{ids['section_id']}/sessions",
            headers=auth_headers,
        )
        assert resp.json()[0]["submission_count"] == 1

    async def test_list_sessions_unenrolled(self, client: AsyncClient, auth_headers: dict):
        ids = await _setup_full_session(client, auth_headers)

        # Create a new user not enrolled in this section
        otp_resp = await client.post(
            "/api/v1/auth/otp/request",
            json={"email": "stranger@uni.edu"},
        )
        code = otp_resp.json()["_dev_code"]
        await client.post(
            "/api/v1/auth/otp/verify",
            json={"email": "stranger@uni.edu", "code": code},
        )

        resp = await client.get(
            f"/api/v1/sections/{ids['section_id']}/sessions",
            headers=_student_headers("stranger@uni.edu"),
        )
        assert resp.status_code == 403
