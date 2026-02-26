from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InstructorTA(Base):
    """Admin-managed TA assignments at the instructor level."""

    __tablename__ = "instructor_tas"

    instructor_email: Mapped[str] = mapped_column(
        String(320), ForeignKey("users.email"), primary_key=True
    )
    ta_email: Mapped[str] = mapped_column(
        String(320), ForeignKey("users.email"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[str] = mapped_column(String(320), ForeignKey("users.email"))
