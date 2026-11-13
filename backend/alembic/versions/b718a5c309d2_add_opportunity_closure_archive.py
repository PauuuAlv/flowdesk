"""add opportunity closure and archive

Revision ID: b718a5c309d2
Revises: 9d731e4ab2f0
Create Date: 2026-11-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b718a5c309d2"
down_revision: Union[str, None] = "9d731e4ab2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("opportunities", sa.Column("loss_reason", sa.String(50), nullable=True))
    op.add_column("opportunities", sa.Column("loss_detail", sa.String(300), nullable=True))
    op.add_column("opportunities", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_opportunities_archived_at"), "opportunities", ["archived_at"])
    op.execute("""INSERT INTO role_permissions (role_id, permission_code)
        SELECT id, 'opportunities.archive' FROM roles
        WHERE origin='template' AND template_key IN ('admin','supervisor') ON CONFLICT DO NOTHING""")

def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_code='opportunities.archive'")
    op.drop_index(op.f("ix_opportunities_archived_at"), table_name="opportunities")
    op.drop_column("opportunities", "archived_at")
    op.drop_column("opportunities", "loss_detail")
    op.drop_column("opportunities", "loss_reason")
