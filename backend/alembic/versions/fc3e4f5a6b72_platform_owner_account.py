"""cuenta principal de plataforma (la creada con SUPERADMIN_EMAIL)

Agrega platform_admins.is_owner. La API marca al arrancar (y el seed) la
cuenta cuyo correo es SUPERADMIN_EMAIL; esa cuenta no puede cambiar de rol ni
desactivarse.

Revision ID: fc3e4f5a6b72
Revises: fb2d3e4f5a61
"""
from alembic import op
import sqlalchemy as sa

revision = "fc3e4f5a6b72"
down_revision = "fb2d3e4f5a61"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "platform_admins",
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("platform_admins", "is_owner")
