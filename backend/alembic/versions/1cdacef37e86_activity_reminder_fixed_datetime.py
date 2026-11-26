"""recordatorios de actividad con fecha y hora exacta

Revision ID: 1cdacef37e86
Revises: 72da15cc5636
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "1cdacef37e86"
down_revision: Union[str, None] = "72da15cc5636"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("activity_reminders", sa.Column("fixed_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("activity_reminders", "minutes_before", existing_type=sa.Integer(), nullable=True)
    op.create_check_constraint("ck_activity_reminder_mode", "activity_reminders",
        "(minutes_before IS NULL) <> (fixed_at IS NULL)")


def downgrade() -> None:
    op.execute("DELETE FROM activity_reminders WHERE minutes_before IS NULL")
    op.drop_constraint("ck_activity_reminder_mode", "activity_reminders", type_="check")
    op.alter_column("activity_reminders", "minutes_before", existing_type=sa.Integer(), nullable=False)
    op.drop_column("activity_reminders", "fixed_at")
