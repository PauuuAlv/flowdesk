"""add billing email and platform audit

Revision ID: f75d5f9e3da8
Revises: f74c4e8d2c97
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f75d5f9e3da8"
down_revision: Union[str, None] = "f74c4e8d2c97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("billing_email", sa.String(255), nullable=True))
    op.execute("UPDATE tenants SET billing_email = contact_email WHERE billing_email IS NULL")
    op.execute(
        """UPDATE tenants SET billing_email = users.email FROM users
        WHERE users.tenant_id = tenants.id AND users.role = 'admin'
        AND tenants.billing_email IS NULL"""
    )
    op.create_table(
        "platform_audit_logs",
        sa.Column("platform_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["platform_admin_id"], ["platform_admins.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_audit_logs_action", "platform_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_platform_audit_logs_action", table_name="platform_audit_logs")
    op.drop_table("platform_audit_logs")
    op.drop_column("tenants", "billing_email")
