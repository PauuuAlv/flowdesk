"""link quote items products

Revision ID: f31b4d1c7a20
Revises: f21a6d982c04
Create Date: 2026-11-14
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "f31b4d1c7a20"
down_revision = "f21a6d982c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("quote_items", sa.Column("product_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_quote_items_product", "quote_items", "products", ["product_id"], ["id"])
    op.create_index(op.f("ix_quote_items_product_id"), "quote_items", ["product_id"])


def downgrade():
    op.drop_index(op.f("ix_quote_items_product_id"), table_name="quote_items")
    op.drop_constraint("fk_quote_items_product", "quote_items", type_="foreignkey")
    op.drop_column("quote_items", "product_id")
