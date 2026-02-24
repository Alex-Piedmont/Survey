import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False
    )
    presentation_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("presentation_types.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    memberships = relationship(
        "TeamMembership", back_populates="team", cascade="all, delete-orphan"
    )


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    student_email: Mapped[str] = mapped_column(
        String(320), ForeignKey("users.email"), primary_key=True
    )

    team = relationship("Team", back_populates="memberships")
