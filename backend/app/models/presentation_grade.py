import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PresentationGrade(Base):
    __tablename__ = "presentation_grades"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id"), nullable=False
    )
    grade: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "A", "B+", "92"
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by: Mapped[str] = mapped_column(
        String(320), ForeignKey("users.email"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
