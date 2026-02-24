import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


async def _setup_full_session(client: AsyncClient, auth_headers: dict) -> dict:
    """Minimal setup for WebSocket testing."""
    resp = await client.post(
        "/api/v1/courses",
        json={"name": "WS Test", "term": "Spring 2026"},
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

    return {"session_id": session_id, "team_id": team_id}


class TestWebSocket:
    async def test_websocket_connect(self, client: AsyncClient, auth_headers: dict):
        """Test that WebSocket connection can be established."""
        from starlette.testclient import TestClient
        from app.main import app

        ids = await _setup_full_session(client, auth_headers)

        # Use synchronous TestClient for WebSocket testing
        with TestClient(app) as sync_client:
            with sync_client.websocket_connect(f"/ws/sessions/{ids['session_id']}") as ws:
                # Connection established successfully
                ws.send_text("ping")
                # If we get here without exception, connection works
