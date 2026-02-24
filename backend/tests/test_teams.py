import pytest
from httpx import AsyncClient


async def _setup_course_section_enrolled(
    client: AsyncClient, auth_headers: dict
) -> tuple[str, str, str]:
    """Create course, section, presentation type, and enroll students.
    Returns (course_id, section_id, ptype_id)."""
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

    # Enroll students
    await client.post(
        f"/api/v1/sections/{section_id}/enroll",
        json={"emails": "alice@uni.edu\nbob@uni.edu\ncharlie@uni.edu"},
        headers=auth_headers,
    )

    # Create presentation type
    resp = await client.post(
        f"/api/v1/courses/{course_id}/presentation-types",
        json={"name": "Debates"},
        headers=auth_headers,
    )
    ptype_id = resp.json()["id"]

    return course_id, section_id, ptype_id


class TestCreateTeam:
    async def test_create_team_with_members(self, client: AsyncClient, auth_headers: dict):
        _, section_id, ptype_id = await _setup_course_section_enrolled(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={
                "name": "Team Alpha",
                "presentation_type_id": ptype_id,
                "member_emails": ["alice@uni.edu", "bob@uni.edu"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Team Alpha"
        assert set(data["members"]) == {"alice@uni.edu", "bob@uni.edu"}

    async def test_create_team_without_members(self, client: AsyncClient, auth_headers: dict):
        _, section_id, ptype_id = await _setup_course_section_enrolled(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={
                "name": "Team Beta",
                "presentation_type_id": ptype_id,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["members"] == []

    async def test_create_team_rejects_unenrolled_member(
        self, client: AsyncClient, auth_headers: dict
    ):
        _, section_id, ptype_id = await _setup_course_section_enrolled(client, auth_headers)

        resp = await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={
                "name": "Team Gamma",
                "presentation_type_id": ptype_id,
                "member_emails": ["notareal@student.edu"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestListTeams:
    async def test_list_teams(self, client: AsyncClient, auth_headers: dict):
        _, section_id, ptype_id = await _setup_course_section_enrolled(client, auth_headers)

        await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={"name": "Team Alpha", "presentation_type_id": ptype_id},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={"name": "Team Beta", "presentation_type_id": ptype_id},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/sections/{section_id}/teams",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_teams_filter_by_ptype(self, client: AsyncClient, auth_headers: dict):
        course_id, section_id, ptype_id = await _setup_course_section_enrolled(
            client, auth_headers
        )

        # Create a second presentation type
        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Headlines"},
            headers=auth_headers,
        )
        ptype2_id = resp.json()["id"]

        await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={"name": "Debate Team", "presentation_type_id": ptype_id},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/sections/{section_id}/teams",
            json={"name": "Headlines Team", "presentation_type_id": ptype2_id},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/sections/{section_id}/teams",
            params={"presentation_type_id": ptype_id},
            headers=auth_headers,
        )
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Debate Team"


class TestUpdateTeamMembers:
    async def test_update_members(self, client: AsyncClient, auth_headers: dict):
        _, section_id, ptype_id = await _setup_course_section_enrolled(client, auth_headers)

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

        # Replace members
        resp = await client.put(
            f"/api/v1/teams/{team_id}/members",
            json={"member_emails": ["bob@uni.edu", "charlie@uni.edu"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert set(resp.json()["members"]) == {"bob@uni.edu", "charlie@uni.edu"}
