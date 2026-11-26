"""recordatorios de actividades

Revision ID: 72da15cc5636
Revises: c9292347a9c6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "72da15cc5636"
down_revision: Union[str, None] = "c9292347a9c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_reminders",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("minutes_before", sa.Integer(), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_reminders_tenant_id", "activity_reminders", ["tenant_id"])
    op.create_index("ix_activity_reminders_activity_id", "activity_reminders", ["activity_id"])
    op.create_index("ix_activity_reminders_remind_at", "activity_reminders", ["remind_at"])
    op.create_index("ix_activity_reminders_sent_at", "activity_reminders", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_activity_reminders_sent_at", table_name="activity_reminders")
    op.drop_index("ix_activity_reminders_remind_at", table_name="activity_reminders")
    op.drop_index("ix_activity_reminders_activity_id", table_name="activity_reminders")
    op.drop_index("ix_activity_reminders_tenant_id", table_name="activity_reminders")
    op.drop_table("activity_reminders")
