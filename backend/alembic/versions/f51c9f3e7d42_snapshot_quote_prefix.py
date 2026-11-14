"""snapshot quote prefix

Revision ID: f51c9f3e7d42
Revises: f41b8e2d6c31
"""
from alembic import op
import sqlalchemy as sa

revision = "f51c9f3e7d42"
down_revision = "f41b8e2d6c31"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quotes", sa.Column("prefix", sa.String(12), nullable=False, server_default="COT"))


def downgrade():
    op.drop_column("quotes", "prefix")
