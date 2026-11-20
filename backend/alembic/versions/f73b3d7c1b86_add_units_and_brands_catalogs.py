"""add tenant measurement units and brands catalogs

Revision ID: f73b3d7c1b86
Revises: f72a2c6b0a75
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f73b3d7c1b86"
down_revision: Union[str, None] = "f72a2c6b0a75"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "measurement_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(50), nullable=False), sa.Column("name", sa.String(80), nullable=False),
        sa.Column("abbreviation", sa.String(15), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_measurement_unit_tenant_key"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_measurement_unit_tenant_name"),
    )
    op.create_index("ix_measurement_units_tenant_id", "measurement_units", ["tenant_id"])
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False), sa.Column("description", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("tenant_id", "name", name="uq_brand_tenant_name"),
    )
    op.create_index("ix_brands_tenant_id", "brands", ["tenant_id"])
    op.execute("""
        INSERT INTO measurement_units (id, tenant_id, key, name, abbreviation, is_active)
        SELECT gen_random_uuid(), t.id, v.key, v.name, v.abbreviation, true FROM tenants t
        CROSS JOIN (VALUES ('piece','Pieza','pza'),('service','Servicio','serv'),('hour','Hora','h'),
          ('day','Día','día'),('month','Mes','mes'),('license','Licencia','lic'),('package','Paquete','paq'))
          AS v(key,name,abbreviation)
    """)
    op.add_column("products", sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("products", sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_products_unit_id", "products", "measurement_units", ["unit_id"], ["id"])
    op.create_foreign_key("fk_products_brand_id", "products", "brands", ["brand_id"], ["id"])
    op.execute("""UPDATE products p SET unit_id = u.id FROM measurement_units u WHERE u.tenant_id = p.tenant_id AND u.key = p.unit""")
    op.alter_column("products", "unit_id", nullable=False)
    op.create_index("ix_products_unit_id", "products", ["unit_id"])
    op.create_index("ix_products_brand_id", "products", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_products_brand_id", table_name="products"); op.drop_index("ix_products_unit_id", table_name="products")
    op.drop_constraint("fk_products_brand_id", "products", type_="foreignkey"); op.drop_constraint("fk_products_unit_id", "products", type_="foreignkey")
    op.drop_column("products", "brand_id"); op.drop_column("products", "unit_id")
    op.drop_index("ix_brands_tenant_id", table_name="brands"); op.drop_table("brands")
    op.drop_index("ix_measurement_units_tenant_id", table_name="measurement_units"); op.drop_table("measurement_units")
