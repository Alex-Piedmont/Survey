import uuid
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id"), nullable=False
    )
    presentation_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("presentation_types.id"), nullable=False
    )
    template_snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("survey_templates.id"), nullable=False
    )
    session_date: Mapped[str] = mapped_column(Date, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session_teams = relationship(
        "SessionTeam", back_populates="session", cascade="all, delete-orphan"
    )


class SessionTeam(Base):
    __tablename__ = "session_teams"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id"), primary_key=True
    )

    session = relationship("Session", back_populates="session_teams")
