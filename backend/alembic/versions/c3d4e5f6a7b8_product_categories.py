"""catálogo de categorías de productos y servicios

Crea product_categories y cambia products.category (texto libre) por
products.category_id. Las categorías que ya se habían escrito pasan al
catálogo de su empresa (una por nombre, sin distinguir mayúsculas) y cada
producto queda ligado a la suya, así que no se pierde ninguna.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_product_category_tenant_name"),
    )
    op.create_index("ix_product_categories_tenant_id", "product_categories", ["tenant_id"])

    # Categorías ya escritas en productos → catálogo (se respeta la primera forma escrita).
    op.execute(
        """
        INSERT INTO product_categories (id, tenant_id, name, is_active)
        SELECT gen_random_uuid(), tenant_id, MIN(TRIM(category)), true
        FROM products
        WHERE category IS NOT NULL AND TRIM(category) <> ''
        GROUP BY tenant_id, LOWER(TRIM(category))
        """
    )
    op.add_column("products", sa.Column("category_id", UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE products AS p SET category_id = c.id
        FROM product_categories AS c
        WHERE c.tenant_id = p.tenant_id AND LOWER(c.name) = LOWER(TRIM(p.category))
        """
    )
    op.create_foreign_key("fk_products_category", "products", "product_categories", ["category_id"], ["id"])
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.drop_index("ix_products_category", table_name="products")
    op.drop_column("products", "category")


def downgrade():
    op.add_column("products", sa.Column("category", sa.String(80), nullable=True))
    op.execute(
        """
        UPDATE products AS p SET category = c.name
        FROM product_categories AS c WHERE c.id = p.category_id
        """
    )
    op.create_index("ix_products_category", "products", ["category"])
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_constraint("fk_products_category", "products", type_="foreignkey")
    op.drop_column("products", "category_id")
    op.drop_index("ix_product_categories_tenant_id", table_name="product_categories")
    op.drop_table("product_categories")
