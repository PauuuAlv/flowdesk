"""add per-item quote discounts

Revision ID: f74c4e8d2c97
Revises: f73b3d7c1b86
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f74c4e8d2c97"
down_revision: Union[str, None] = "f73b3d7c1b86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quote_items", sa.Column("gross_amount", sa.Numeric(14,2), nullable=True))
    op.add_column("quote_items", sa.Column("discount_percent", sa.Numeric(5,2), nullable=False, server_default="0"))
    op.add_column("quote_items", sa.Column("discount_amount", sa.Numeric(14,2), nullable=False, server_default="0"))
    op.execute("UPDATE quote_items SET gross_amount = amount WHERE gross_amount IS NULL")
    op.alter_column("quote_items", "gross_amount", nullable=False)
    op.alter_column("quote_items", "discount_percent", server_default=None)
    op.alter_column("quote_items", "discount_amount", server_default=None)


def downgrade() -> None:
    op.drop_column("quote_items", "discount_amount")
    op.drop_column("quote_items", "discount_percent")
    op.drop_column("quote_items", "gross_amount")
