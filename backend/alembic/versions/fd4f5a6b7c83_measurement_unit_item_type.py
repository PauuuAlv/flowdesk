"""tipo en unidades de medida (producto / servicio)

Agrega measurement_units.item_type para separar las unidades de los productos
de las de los servicios. Las unidades por defecto se clasifican por su clave;
las personalizadas, por el tipo de los productos que ya las usan (si no tienen
productos, quedan como "product").

Revision ID: fd4f5a6b7c83
Revises: fc3e4f5a6b72
"""
from alembic import op
import sqlalchemy as sa

revision = "fd4f5a6b7c83"
down_revision = "fc3e4f5a6b72"
branch_labels = None
depends_on = None

SERVICE_TEMPLATE_KEYS = ("service", "hour", "day", "month")


def upgrade():
    op.add_column(
        "measurement_units",
        sa.Column("item_type", sa.String(20), nullable=False, server_default="product"),
    )
    keys = ", ".join(f"'{key}'" for key in SERVICE_TEMPLATE_KEYS)
    op.execute(f"UPDATE measurement_units SET item_type = 'service' WHERE key IN ({keys})")
    # Unidades personalizadas que hoy solo usan servicios.
    op.execute(
        """
        UPDATE measurement_units u SET item_type = 'service'
        WHERE u.key NOT IN ('piece', 'license', 'package')
          AND EXISTS (SELECT 1 FROM products p WHERE p.unit_id = u.id)
          AND NOT EXISTS (SELECT 1 FROM products p WHERE p.unit_id = u.id AND p.item_type <> 'service')
        """
    )
    op.create_check_constraint(
        "ck_measurement_units_item_type", "measurement_units", "item_type IN ('product', 'service')"
    )
    op.create_index("ix_measurement_units_tenant_type", "measurement_units", ["tenant_id", "item_type"])


def downgrade():
    op.drop_index("ix_measurement_units_tenant_type", table_name="measurement_units")
    op.drop_constraint("ck_measurement_units_item_type", "measurement_units", type_="check")
    op.drop_column("measurement_units", "item_type")
