"""add company settings

Revision ID: f41b8e2d6c31
Revises: f31b4d1c7a20
"""
from alembic import op
import sqlalchemy as sa

revision = "f41b8e2d6c31"
down_revision = "f31b4d1c7a20"
branch_labels = None
depends_on = None


def upgrade():
    columns = (
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("tax_id", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("address_line", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(12), nullable=True),
        sa.Column("country", sa.String(80), nullable=False, server_default="México"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MXN"),
        sa.Column("default_tax_rate", sa.Numeric(5, 2), nullable=False, server_default="16"),
        sa.Column("quote_validity_days", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("quote_prefix", sa.String(12), nullable=False, server_default="COT"),
        sa.Column("payment_instructions", sa.Text(), nullable=True),
    )
    for column in columns:
        op.add_column("tenants", column)
    op.execute("""INSERT INTO role_permissions(role_id, permission_code)
        SELECT id, permission FROM roles CROSS JOIN LATERAL
        unnest(CASE WHEN template_key = 'admin' THEN ARRAY['settings.view','settings.update']
                    ELSE ARRAY['settings.view'] END) permission
        WHERE origin = 'template' ON CONFLICT DO NOTHING""")


def downgrade():
    op.execute("DELETE FROM role_permissions WHERE permission_code LIKE 'settings.%'")
    for name in ("payment_instructions", "quote_prefix", "quote_validity_days", "default_tax_rate", "currency", "country", "postal_code", "state", "city", "address_line", "logo_url", "website", "contact_phone", "contact_email", "tax_id", "legal_name"):
        op.drop_column("tenants", name)
