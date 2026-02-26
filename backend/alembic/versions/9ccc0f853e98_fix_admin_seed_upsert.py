"""fix_admin_seed_upsert

Revision ID: 9ccc0f853e98
Revises: bb8cf6c73062
Create Date: 2026-02-26 15:36:30.585841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ccc0f853e98'
down_revision: Union[str, Sequence[str], None] = 'bb8cf6c73062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure alex@aptuslearning.ai has admin + instructor flags."""
    op.execute(
        """
        INSERT INTO users (email, is_admin, is_instructor, created_at)
        VALUES ('alex@aptuslearning.ai', true, true, now())
        ON CONFLICT (email) DO UPDATE
            SET is_admin = true, is_instructor = true
        """
    )


def downgrade() -> None:
    """Revert admin flags (best-effort)."""
    op.execute(
        """
        UPDATE users SET is_admin = false, is_instructor = false
        WHERE email = 'alex@aptuslearning.ai'
        """
    )
