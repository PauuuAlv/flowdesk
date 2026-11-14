"""add products

Revision ID: f21a6d982c04
Revises: e8a731df409c
Create Date: 2026-11-14
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "f21a6d982c04"
down_revision = "e8a731df409c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table("products", sa.Column("name", sa.String(140), nullable=False), sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True), sa.Column("category", sa.String(80), nullable=True),
        sa.Column("item_type", sa.String(20), nullable=False), sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("base_price", sa.Numeric(14, 2), nullable=False), sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"))
    for column in ("name", "sku", "category", "item_type", "status", "tenant_id"):
        op.create_index(op.f(f"ix_products_{column}"), "products", [column])
    op.execute("""INSERT INTO role_permissions(role_id,permission_code) SELECT id,p FROM roles CROSS JOIN LATERAL unnest(CASE WHEN template_key IN ('admin','supervisor') THEN ARRAY['products.view','products.create','products.update','products.delete'] ELSE ARRAY['products.view'] END) p WHERE origin='template' ON CONFLICT DO NOTHING""")


def downgrade():
    op.execute("DELETE FROM role_permissions WHERE permission_code LIKE 'products.%'")
    op.drop_table("products")
