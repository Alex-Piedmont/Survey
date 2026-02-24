"""Email notification service for late submissions.

Stubs SendGrid integration. When SENDGRID_API_KEY is set, sends real emails.
Otherwise, logs the notification for testing.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.session import Session

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    to_emails: list[str]
    subject: str
    body: str


# In-memory log for testing (when SendGrid is not configured)
sent_notifications: list[Notification] = field(default_factory=list)
sent_notifications = []


async def _get_instructor_and_ta_emails(db: AsyncSession, session: Session) -> list[str]:
    """Get instructor and TA emails for a session's section/course."""
    section = await db.execute(select(Section).where(Section.id == session.section_id))
    section = section.scalar_one()

    result = await db.execute(
        select(Enrollment.student_email)
        .join(Section, Enrollment.section_id == Section.id)
        .where(
            Section.course_id == section.course_id,
            Enrollment.role.in_(["instructor", "ta"]),
        )
    )
    return [row[0] for row in result.all()]


async def notify_late_submission(
    db: AsyncSession,
    session: Session,
    student_email: str,
    penalty_pct: int,
):
    """Send notification about a late submission to instructor and TAs."""
    recipients = await _get_instructor_and_ta_emails(db, session)
    if not recipients:
        return

    subject = f"Late Submission: {student_email} ({penalty_pct}% penalty)"
    body = (
        f"Student {student_email} submitted feedback late for session "
        f"on {session.session_date}.\n\n"
        f"Penalty: {penalty_pct}%\n"
        f"Session ID: {session.id}"
    )

    notification = Notification(to_emails=recipients, subject=subject, body=body)

    sendgrid_key = getattr(settings, "SENDGRID_API_KEY", None)
    if sendgrid_key:
        # Real SendGrid integration
        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_key)
            from_email = Email(getattr(settings, "FROM_EMAIL", "noreply@classroom-survey.edu"))
            for recipient in recipients:
                message = Mail(
                    from_email=from_email,
                    to_emails=To(recipient),
                    subject=subject,
                    plain_text_content=Content("text/plain", body),
                )
                sg.client.mail.send.post(request_body=message.get())
            logger.info(f"Sent late notification email to {recipients}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    else:
        # Stub mode: log for testing
        logger.info(f"[STUB] Late notification: {subject} -> {recipients}")
        sent_notifications.append(notification)


def clear_notifications():
    """Clear the in-memory notification log (for testing)."""
    sent_notifications.clear()
