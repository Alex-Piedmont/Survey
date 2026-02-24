import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "student_email",
            "target_team_id",
            "target_student_email",
            "version",
            name="uq_submission_version",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    student_email: Mapped[str] = mapped_column(
        String(320), ForeignKey("users.email"), nullable=False, index=True
    )
    target_team_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teams.id"), nullable=True
    )
    target_student_email: Mapped[str | None] = mapped_column(
        String(320), nullable=True
    )
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    responses: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    penalty_pct: Mapped[int] = mapped_column(Integer, default=0)
