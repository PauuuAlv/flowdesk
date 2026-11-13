"""add opportunities

Revision ID: 9d731e4ab2f0
Revises: 8b32fd91a4e7
Create Date: 2026-11-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "9d731e4ab2f0"
down_revision: Union[str, None] = "8b32fd91a4e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("client_id", sa.UUID(), nullable=False), sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(140), nullable=False), sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False), sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True), sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]), sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]), sa.PrimaryKeyConstraint("id"),
    )
    for column in ("client_id", "owner_user_id", "name", "stage", "tenant_id"):
        op.create_index(op.f(f"ix_opportunities_{column}"), "opportunities", [column])
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT id, permission FROM roles CROSS JOIN LATERAL unnest(
          CASE template_key
            WHEN 'admin' THEN ARRAY['opportunities.view','opportunities.create','opportunities.update','opportunities.close']
            WHEN 'supervisor' THEN ARRAY['opportunities.view','opportunities.create','opportunities.update','opportunities.close']
            ELSE ARRAY['opportunities.view'] END
        ) permission WHERE origin='template' ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_code LIKE 'opportunities.%'")
    op.drop_table("opportunities")
