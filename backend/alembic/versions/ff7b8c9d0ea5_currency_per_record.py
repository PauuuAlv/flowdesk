"""moneda por oportunidad y por producto/servicio

Agrega opportunities.currency y products.currency (las cotizaciones ya tenían
quotes.currency). Los registros existentes toman la moneda configurada de su
empresa (tenants.currency).

Revision ID: ff7b8c9d0ea5
Revises: fe6a7b8c9d94
"""
from alembic import op
import sqlalchemy as sa

revision = "ff7b8c9d0ea5"
down_revision = "fe6a7b8c9d94"
branch_labels = None
depends_on = None

TABLES = ("opportunities", "products")


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("currency", sa.String(3), nullable=False, server_default="MXN"))
        op.execute(
            f"""
            UPDATE {table} AS t SET currency = tenants.currency
            FROM tenants
            WHERE tenants.id = t.tenant_id AND tenants.currency IN ('MXN', 'USD')
            """
        )
        op.create_check_constraint(f"ck_{table}_currency", table, "currency IN ('MXN', 'USD')")
    op.create_check_constraint("ck_quotes_currency", "quotes", "currency IN ('MXN', 'USD')")


def downgrade():
    op.drop_constraint("ck_quotes_currency", "quotes", type_="check")
    for table in TABLES:
        op.drop_constraint(f"ck_{table}_currency", table, type_="check")
        op.drop_column(table, "currency")
