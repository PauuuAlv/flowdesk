"""recuperación de contraseña para el equipo de plataforma

Agrega platform_admins.password_reset_token_hash y password_reset_expires_at
para el flujo "¿Olvidaste tu contraseña?" del login de administración.

Revision ID: fe6a7b8c9d94
Revises: fd4f5a6b7c83
"""
from alembic import op
import sqlalchemy as sa

revision = "fe6a7b8c9d94"
down_revision = "fd4f5a6b7c83"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("platform_admins", sa.Column("password_reset_token_hash", sa.String(64), nullable=True))
    op.add_column("platform_admins", sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(
        "uq_platform_admins_password_reset_token_hash", "platform_admins", ["password_reset_token_hash"]
    )


def downgrade():
    op.drop_constraint("uq_platform_admins_password_reset_token_hash", "platform_admins", type_="unique")
    op.drop_column("platform_admins", "password_reset_expires_at")
    op.drop_column("platform_admins", "password_reset_token_hash")
