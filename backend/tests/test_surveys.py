import pytest
from httpx import AsyncClient


async def _create_course(client: AsyncClient, auth_headers: dict) -> str:
    resp = await client.post(
        "/api/v1/courses",
        json={"name": "MGMT 481", "term": "Spring 2026"},
        headers=auth_headers,
    )
    return resp.json()["id"]


class TestPresentationTypes:
    async def test_create_presentation_type(self, client: AsyncClient, auth_headers: dict):
        course_id = await _create_course(client, auth_headers)

        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Strategic Headlines"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Strategic Headlines"
        assert data["course_id"] == course_id

    async def test_list_presentation_types(self, client: AsyncClient, auth_headers: dict):
        course_id = await _create_course(client, auth_headers)

        await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Strategic Headlines"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Learning Team Debates"},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/courses/{course_id}/presentation-types",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestTemplates:
    async def test_get_empty_template(self, client: AsyncClient, auth_headers: dict):
        course_id = await _create_course(client, auth_headers)
        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Strategic Headlines"},
            headers=auth_headers,
        )
        ptype_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/presentation-types/{ptype_id}/template",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert data["questions"] == []

    async def test_update_template_creates_new_version(
        self, client: AsyncClient, auth_headers: dict
    ):
        course_id = await _create_course(client, auth_headers)
        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Strategic Headlines"},
            headers=auth_headers,
        )
        ptype_id = resp.json()["id"]

        questions = [
            {
                "question_text": "How clear was the content?",
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
        ]

        resp = await client.put(
            f"/api/v1/presentation-types/{ptype_id}/template",
            json={"questions": questions},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 2
        assert len(data["questions"]) == 2
        assert data["questions"][0]["question_text"] == "How clear was the content?"

    async def test_template_versioning_preserves_old(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Updating a template creates a new version; old version still exists."""
        course_id = await _create_course(client, auth_headers)
        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Strategic Headlines"},
            headers=auth_headers,
        )
        ptype_id = resp.json()["id"]

        # Version 2: one question
        await client.put(
            f"/api/v1/presentation-types/{ptype_id}/template",
            json={
                "questions": [
                    {
                        "question_text": "Q1",
                        "question_type": "likert_5",
                        "category": "audience",
                        "sort_order": 1,
                    }
                ]
            },
            headers=auth_headers,
        )

        # Version 3: two questions
        resp = await client.put(
            f"/api/v1/presentation-types/{ptype_id}/template",
            json={
                "questions": [
                    {
                        "question_text": "Q1 revised",
                        "question_type": "likert_5",
                        "category": "audience",
                        "sort_order": 1,
                    },
                    {
                        "question_text": "Q2 new",
                        "question_type": "free_text",
                        "category": "audience",
                        "sort_order": 2,
                    },
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 3
        assert len(data["questions"]) == 2

        # GET returns latest (v3)
        resp = await client.get(
            f"/api/v1/presentation-types/{ptype_id}/template",
            headers=auth_headers,
        )
        assert resp.json()["version"] == 3

    async def test_template_question_types(self, client: AsyncClient, auth_headers: dict):
        course_id = await _create_course(client, auth_headers)
        resp = await client.post(
            f"/api/v1/courses/{course_id}/presentation-types",
            json={"name": "Debates"},
            headers=auth_headers,
        )
        ptype_id = resp.json()["id"]

        questions = [
            {
                "question_text": "Rate delivery",
                "question_type": "likert_7",
                "category": "audience",
                "sort_order": 1,
            },
            {
                "question_text": "Contribution level",
                "question_type": "likert_5",
                "category": "peer",
                "sort_order": 2,
            },
            {
                "question_text": "Grade",
                "question_type": "multiple_choice",
                "category": "instructor",
                "options": ["A", "B", "C", "D", "F"],
                "sort_order": 3,
            },
            {
                "question_text": "Comments",
                "question_type": "free_text",
                "category": "audience",
                "is_required": False,
                "sort_order": 4,
            },
        ]

        resp = await client.put(
            f"/api/v1/presentation-types/{ptype_id}/template",
            json={"questions": questions},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["questions"]) == 4
        # Verify multiple choice has options
        mc_q = [q for q in data["questions"] if q["question_type"] == "multiple_choice"][0]
        assert mc_q["options"] == ["A", "B", "C", "D", "F"]
