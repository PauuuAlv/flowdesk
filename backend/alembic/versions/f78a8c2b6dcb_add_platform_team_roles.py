"""add platform team roles

Revision ID: f78a8c2b6dcb
Revises: f77f7b1a5fca
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f78a8c2b6dcb"
down_revision: Union[str, None] = "f77f7b1a5fca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("platform_admins", sa.Column("role", sa.String(30), nullable=False, server_default="viewer"))
    op.add_column("platform_admins", sa.Column("invitation_token_hash", sa.String(64), nullable=True))
    op.add_column("platform_admins", sa.Column("invitation_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("platform_admins", "hashed_password", nullable=True)
    op.create_unique_constraint("uq_platform_admin_invitation_token", "platform_admins", ["invitation_token_hash"])
    op.execute("UPDATE platform_admins SET role = 'superadmin' WHERE hashed_password IS NOT NULL")
    op.alter_column("platform_admins", "role", server_default=None)


def downgrade() -> None:
    op.execute("DELETE FROM platform_admins WHERE hashed_password IS NULL")
    op.drop_constraint("uq_platform_admin_invitation_token", "platform_admins", type_="unique")
    op.alter_column("platform_admins", "hashed_password", nullable=False)
    op.drop_column("platform_admins", "invitation_expires_at")
    op.drop_column("platform_admins", "invitation_token_hash")
    op.drop_column("platform_admins", "role")
