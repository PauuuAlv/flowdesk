"""add contacts

EPIC-006: contactos por cliente con un único contacto principal.
Crea un contacto principal para cada cliente existente a partir de
clients.contact_name / email / phone, para no perder información.

Revision ID: fa1c2d3e4f50
Revises: c9e5a1d3f742
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fa1c2d3e4f50"
down_revision: Union[str, None] = "c9e5a1d3f742"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contacts_tenant_id"), "contacts", ["tenant_id"])
    op.create_index(op.f("ix_contacts_client_id"), "contacts", ["client_id"])
    op.create_index(
        "uq_contacts_primary_per_client",
        "contacts",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )

    op.execute(
        """
        INSERT INTO contacts (id, tenant_id, client_id, full_name, email, phone, is_primary)
        SELECT gen_random_uuid(), c.tenant_id, c.id, c.contact_name, c.email, c.phone, true
        FROM clients c
        """
    )


def downgrade() -> None:
    op.drop_index("uq_contacts_primary_per_client", table_name="contacts")
    op.drop_index(op.f("ix_contacts_client_id"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_tenant_id"), table_name="contacts")
    op.drop_table("contacts")
