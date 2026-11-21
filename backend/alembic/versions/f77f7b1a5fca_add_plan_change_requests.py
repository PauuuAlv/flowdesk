"""add plan change requests

Revision ID: f77f7b1a5fca
Revises: f76e6a0f4eb9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f77f7b1a5fca"
down_revision: Union[str, None] = "f76e6a0f4eb9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_change_requests",
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_plan_key", sa.String(30), nullable=False),
        sa.Column("requested_plan_key", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("resolved_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by_admin_id"], ["platform_admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_change_requests_tenant_id", "plan_change_requests", ["tenant_id"])
    op.create_index("ix_plan_change_requests_status", "plan_change_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_plan_change_requests_status", table_name="plan_change_requests")
    op.drop_index("ix_plan_change_requests_tenant_id", table_name="plan_change_requests")
    op.drop_table("plan_change_requests")
