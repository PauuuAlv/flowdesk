"""add clients

Revision ID: 8b32fd91a4e7
Revises: c41f8d9a2b10
Create Date: 2026-11-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b32fd91a4e7"
down_revision: Union[str, None] = "c41f8d9a2b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("company_name", sa.String(length=120), nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_client_tenant_email"),
    )
    op.create_index(op.f("ix_clients_company_name"), "clients", ["company_name"])
    op.create_index(op.f("ix_clients_email"), "clients", ["email"])
    op.create_index(op.f("ix_clients_status"), "clients", ["status"])
    op.create_index(op.f("ix_clients_tenant_id"), "clients", ["tenant_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_clients_tenant_id"), table_name="clients")
    op.drop_index(op.f("ix_clients_status"), table_name="clients")
    op.drop_index(op.f("ix_clients_email"), table_name="clients")
    op.drop_index(op.f("ix_clients_company_name"), table_name="clients")
    op.drop_table("clients")
