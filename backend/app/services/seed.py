"""Seed default survey templates for common presentation types (FR-11)."""

DEFAULT_TEMPLATES = {
    "Strategic Headlines": {
        "questions": [
            {"question_text": "How clearly did the team present their strategic analysis?", "question_type": "likert_5", "category": "audience", "sort_order": 1},
            {"question_text": "How well did the team connect their analysis to course concepts?", "question_type": "likert_5", "category": "audience", "sort_order": 2},
            {"question_text": "How engaging was the presentation delivery?", "question_type": "likert_5", "category": "audience", "sort_order": 3},
            {"question_text": "What was the strongest aspect of this presentation?", "question_type": "free_text", "category": "audience", "is_required": False, "sort_order": 4},
            {"question_text": "What could be improved?", "question_type": "free_text", "category": "audience", "is_required": False, "sort_order": 5},
            {"question_text": "How well did this team member contribute to the team's preparation?", "question_type": "likert_5", "category": "peer", "sort_order": 6},
            {"question_text": "How well did this team member contribute to the presentation delivery?", "question_type": "likert_5", "category": "peer", "sort_order": 7},
        ],
    },
    "Learning Team Debates": {
        "questions": [
            {"question_text": "How well did the team argue their position?", "question_type": "likert_5", "category": "audience", "sort_order": 1},
            {"question_text": "How effectively did the team use evidence to support their arguments?", "question_type": "likert_5", "category": "audience", "sort_order": 2},
            {"question_text": "How well did the team respond to counterarguments?", "question_type": "likert_5", "category": "audience", "sort_order": 3},
            {"question_text": "How engaging and persuasive was the debate overall?", "question_type": "likert_5", "category": "audience", "sort_order": 4},
            {"question_text": "Additional comments", "question_type": "free_text", "category": "audience", "is_required": False, "sort_order": 5},
            {"question_text": "How well did this team member contribute to research and preparation?", "question_type": "likert_5", "category": "peer", "sort_order": 6},
            {"question_text": "How well did this team member contribute during the debate?", "question_type": "likert_5", "category": "peer", "sort_order": 7},
        ],
    },
    "Class Strategy Project": {
        "questions": [
            {"question_text": "How clearly did the team present their strategy?", "question_type": "likert_5", "category": "audience", "sort_order": 1},
            {"question_text": "How thorough was the team's analysis?", "question_type": "likert_5", "category": "audience", "sort_order": 2},
            {"question_text": "How realistic and actionable were the team's recommendations?", "question_type": "likert_5", "category": "audience", "sort_order": 3},
            {"question_text": "How professional was the presentation quality (slides, delivery)?", "question_type": "likert_5", "category": "audience", "sort_order": 4},
            {"question_text": "What was the strongest aspect of this presentation?", "question_type": "free_text", "category": "audience", "is_required": False, "sort_order": 5},
            {"question_text": "What recommendations do you have for improvement?", "question_type": "free_text", "category": "audience", "is_required": False, "sort_order": 6},
            {"question_text": "How well did this team member contribute to the project?", "question_type": "likert_5", "category": "peer", "sort_order": 7},
            {"question_text": "How reliable was this team member (meeting deadlines, attending meetings)?", "question_type": "likert_5", "category": "peer", "sort_order": 8},
        ],
    },
}


def get_default_template_names() -> list[str]:
    """Get the names of all default template types."""
    return list(DEFAULT_TEMPLATES.keys())


def get_default_questions(template_name: str) -> list[dict]:
    """Get the default questions for a template type."""
    template = DEFAULT_TEMPLATES.get(template_name)
    if template is None:
        return []
    return template["questions"]
