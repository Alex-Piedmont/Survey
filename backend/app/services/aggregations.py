"""Aggregation logic for session dashboard and summary views."""

import statistics

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.session import Session, SessionTeam
from app.models.submission import Submission
from app.models.survey import Question, SurveyTemplate
from app.models.team import TeamMembership


async def get_enrolled_count(db: AsyncSession, section_id: str) -> int:
    """Count students enrolled in a section (excluding instructors/TAs)."""
    result = await db.execute(
        select(func.count()).where(
            Enrollment.section_id == section_id,
            Enrollment.role == "student",
        )
    )
    return result.scalar_one()


async def get_submitted_emails(db: AsyncSession, session_id: str) -> set[str]:
    """Get unique student emails that have submitted for this session."""
    result = await db.execute(
        select(Submission.student_email)
        .where(Submission.session_id == session_id)
        .distinct()
    )
    return {row[0] for row in result.all()}


async def get_enrolled_student_emails(db: AsyncSession, section_id: str) -> set[str]:
    """Get all student emails enrolled in a section."""
    result = await db.execute(
        select(Enrollment.student_email).where(
            Enrollment.section_id == section_id,
            Enrollment.role == "student",
        )
    )
    return {row[0] for row in result.all()}


async def get_presenting_member_emails(
    db: AsyncSession, session_id: str
) -> set[str]:
    """Get emails of all students on presenting teams in this session."""
    result = await db.execute(
        select(TeamMembership.student_email)
        .join(SessionTeam, TeamMembership.team_id == SessionTeam.team_id)
        .where(SessionTeam.session_id == session_id)
    )
    return {row[0] for row in result.all()}


async def get_latest_submissions(
    db: AsyncSession, session_id: str, feedback_type: str | None = None
) -> list[Submission]:
    """Get latest version of each submission for a session."""
    filters = [Submission.session_id == session_id]
    if feedback_type:
        filters.append(Submission.feedback_type == feedback_type)

    # Subquery: max version per (student, target_team, target_student)
    subq = (
        select(
            Submission.student_email,
            Submission.target_team_id,
            Submission.target_student_email,
            func.max(Submission.version).label("max_version"),
        )
        .where(*filters)
        .group_by(
            Submission.student_email,
            Submission.target_team_id,
            Submission.target_student_email,
        )
        .subquery()
    )

    from sqlalchemy import or_

    result = await db.execute(
        select(Submission)
        .join(
            subq,
            (Submission.student_email == subq.c.student_email)
            & (Submission.target_team_id == subq.c.target_team_id)
            & or_(
                Submission.target_student_email == subq.c.target_student_email,
                (Submission.target_student_email.is_(None))
                & (subq.c.target_student_email.is_(None)),
            )
            & (Submission.version == subq.c.max_version),
        )
        .where(*filters)
    )
    return list(result.scalars().all())


def compute_likert_stats(values: list[int | float]) -> dict:
    """Compute stats for a list of Likert-scale values."""
    if not values:
        return {"mean": None, "median": None, "std_dev": None, "count": 0, "histogram": {}}

    hist = {}
    for v in values:
        hist[str(v)] = hist.get(str(v), 0) + 1

    return {
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "std_dev": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        "count": len(values),
        "histogram": hist,
    }


async def aggregate_team_scores(
    db: AsyncSession, session_id: str, template_snapshot_id: str
) -> dict[str, dict]:
    """Aggregate Likert scores per team per question.

    Returns: {team_id: {question_id: {mean, median, std_dev, count, histogram}}}
    """
    # Get Likert question IDs from template snapshot
    template = await db.execute(
        select(Question).where(
            Question.template_id == template_snapshot_id,
            Question.question_type.like("likert%"),
            Question.is_active == True,
        )
    )
    likert_questions = {q.id: q for q in template.scalars().all()}

    if not likert_questions:
        return {}

    submissions = await get_latest_submissions(db, session_id, feedback_type="audience")

    # Group scores: {team_id: {question_id: [values]}}
    team_scores: dict[str, dict[str, list]] = {}
    for sub in submissions:
        tid = sub.target_team_id
        if tid not in team_scores:
            team_scores[tid] = {qid: [] for qid in likert_questions}
        for qid, value in sub.responses.items():
            if qid in likert_questions and isinstance(value, (int, float)):
                team_scores[tid][qid].append(value)

    # Compute stats
    result = {}
    for tid, questions in team_scores.items():
        result[tid] = {}
        for qid, values in questions.items():
            result[tid][qid] = compute_likert_stats(values)

    return result


async def collect_free_text_comments(
    db: AsyncSession, session_id: str, template_snapshot_id: str
) -> dict[str, list[dict]]:
    """Collect free-text comments grouped by target team.

    Returns: {team_id: [{question_id, text, submission_id, withheld}]}
    """
    # Get free-text question IDs
    template = await db.execute(
        select(Question).where(
            Question.template_id == template_snapshot_id,
            Question.question_type == "free_text",
            Question.is_active == True,
        )
    )
    text_questions = {q.id for q in template.scalars().all()}

    if not text_questions:
        return {}

    submissions = await get_latest_submissions(db, session_id, feedback_type="audience")

    comments: dict[str, list[dict]] = {}
    for sub in submissions:
        tid = sub.target_team_id
        if tid not in comments:
            comments[tid] = []
        for qid, value in sub.responses.items():
            if qid in text_questions and isinstance(value, str) and value.strip():
                comments[tid].append({
                    "question_id": qid,
                    "text": value,
                    "submission_id": sub.id,
                    "withheld": sub.withheld,
                })

    return comments


async def build_participation_matrix(
    db: AsyncSession, session_id: str, section_id: str
) -> list[dict]:
    """Build a participation matrix: which students completed feedback for which teams.

    Returns: [{email, submissions: {team_id: bool}, peer_submitted: bool, is_presenter: bool}]
    """
    enrolled = await get_enrolled_student_emails(db, section_id)
    presenter_emails = await get_presenting_member_emails(db, session_id)

    # Get presenting team IDs
    result = await db.execute(
        select(SessionTeam.team_id).where(SessionTeam.session_id == session_id)
    )
    presenting_team_ids = [row[0] for row in result.all()]

    submissions = await get_latest_submissions(db, session_id)

    # Build lookup: {email: {team_id: has_audience, "peer": has_peer}}
    sub_lookup: dict[str, dict] = {}
    for sub in submissions:
        email = sub.student_email
        if email not in sub_lookup:
            sub_lookup[email] = {}
        if sub.feedback_type == "audience" and sub.target_team_id:
            sub_lookup[email][sub.target_team_id] = True
        elif sub.feedback_type == "peer":
            sub_lookup[email]["peer"] = True

    matrix = []
    for email in sorted(enrolled):
        student_subs = sub_lookup.get(email, {})
        team_status = {tid: student_subs.get(tid, False) for tid in presenting_team_ids}
        is_presenter = email in presenter_emails
        matrix.append({
            "email": email,
            "audience_submissions": team_status,
            "peer_submitted": student_subs.get("peer", False),
            "is_presenter": is_presenter,
        })

    return matrix
