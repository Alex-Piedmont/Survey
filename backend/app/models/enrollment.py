from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), primary_key=True
    )
    student_email: Mapped[str] = mapped_column(
        String(320), ForeignKey("users.email"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="student")

    section = relationship("Section", back_populates="enrollments")
