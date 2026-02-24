import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.services.notifications import clear_notifications, sent_notifications


async def _setup_late_session(client: AsyncClient, auth_headers: dict) -> dict:
    """Create a session with a deadline in the past (but within 7 days) for late testing."""
    resp = await client.post(
        "/api/v1/courses",
        json={"name": "Late Course", "term": "Spring 2026"},
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
        json={"emails": "alice@uni.edu\neve@uni.edu"},
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
                    "question_text": "Score",
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
            "member_emails": ["alice@uni.edu"],
        },
        headers=auth_headers,
    )
    team_id = resp.json()["id"]

    # Create session with deadline 2 days ago (still within 7-day window)
    resp = await client.post(
        "/api/v1/sessions",
        json={
            "section_id": section_id,
            "presentation_type_id": ptype_id,
            "presenting_team_ids": [team_id],
            "session_date": "2026-02-20",
            "deadline": "2026-02-22T00:29:00Z",
        },
        headers=auth_headers,
    )
    session_id = resp.json()["id"]

    # Get question IDs
    resp = await client.get(f"/api/v1/s/{session_id}")
    questions = resp.json()["questions"]
    likert_qid = questions[0]["id"]

    return {
        "session_id": session_id,
        "team_id": team_id,
        "likert_qid": likert_qid,
    }


class TestLateNotifications:
    async def test_late_submission_triggers_notification(
        self, client: AsyncClient, auth_headers: dict
    ):
        """A late submission should create a notification for the instructor."""
        clear_notifications()
        ids = await _setup_late_session(client, auth_headers)

        eve_headers = {"Authorization": f"Bearer {create_access_token('eve@uni.edu')}"}
        resp = await client.post(
            f"/api/v1/s/{ids['session_id']}/submit",
            json={
                "target_team_id": ids["team_id"],
                "feedback_type": "audience",
                "responses": {ids["likert_qid"]: 4},
            },
            headers=eve_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_late"] is True

        # Check notification was sent
        assert len(sent_notifications) == 1
        notif = sent_notifications[0]
        assert "eve@uni.edu" in notif.subject
        assert "instructor@university.edu" in notif.to_emails

    async def test_on_time_submission_no_notification(
        self, client: AsyncClient, auth_headers: dict
    ):
        """An on-time submission should NOT trigger a notification."""
        clear_notifications()

        # Setup with future deadline
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "OnTime Course", "term": "Spring 2026"},
            headers=auth_headers,
        )
        course_id = resp.json()["id"]
        resp = await client.post(
            f"/api/v1/courses/{course_id}/sections",
            json={"name": "Sec B"},
            headers=auth_headers,
        )
        section_id = resp.json()["id"]

        await client.post(
            f"/api/v1/sections/{section_id}/enroll",
            json={"emails": "eve@uni.edu"},
            headers=auth_headers,
        )

        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Talks"},
            headers=auth_headers,
        )
        ptype_id = resp.json()["id"]

        await client.put(
            f"/api/v1/presentation-types/{ptype_id}/template",
            json={
                "questions": [
                    {"question_text": "Score", "question_type": "likert_5", "category": "audience", "sort_order": 1},
                ]
            },
            headers=auth_headers,
        )

        resp = await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={"name": "Team B", "presentation_type_id": ptype_id, "member_emails": []},
            headers=auth_headers,
        )
        team_id = resp.json()["id"]

        resp = await client.post(
            "/api/v1/sessions",
            json={
                "section_id": section_id,
                "presentation_type_id": ptype_id,
                "presenting_team_ids": [team_id],
                "session_date": "2026-12-15",
            },
            headers=auth_headers,
        )
        session_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/s/{session_id}")
        qid = resp.json()["questions"][0]["id"]

        eve_headers = {"Authorization": f"Bearer {create_access_token('eve@uni.edu')}"}
        resp = await client.post(
            f"/api/v1/s/{session_id}/submit",
            json={
                "target_team_id": team_id,
                "feedback_type": "audience",
                "responses": {qid: 5},
            },
            headers=eve_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_late"] is False

        # No notification should have been sent
        assert len(sent_notifications) == 0
