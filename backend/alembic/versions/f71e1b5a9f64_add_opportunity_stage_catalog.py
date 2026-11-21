"""add opportunity stage catalog per tenant

Revision ID: f71e1b5a9f64
Revises: f61d0a4f8e53
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f71e1b5a9f64"
down_revision: Union[str, None] = "f61d0a4f8e53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("stage_type", sa.String(length=20), nullable=False),
        sa.Column("default_probability", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_opportunity_stage_tenant_key"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_opportunity_stage_tenant_name"),
    )
    op.create_index("ix_opportunity_stages_tenant_id", "opportunity_stages", ["tenant_id"])
    op.execute("""
        INSERT INTO opportunity_stages
            (id, tenant_id, key, name, position, stage_type, default_probability, is_active)
        SELECT gen_random_uuid(), t.id, v.key, v.name, v.position, v.stage_type, v.probability, true
        FROM tenants t
        CROSS JOIN (VALUES
            ('prospecting', 'Prospecto', 1, 'normal', 10),
            ('contact', 'Contacto', 2, 'normal', 30),
            ('proposal', 'Propuesta', 3, 'normal', 60),
            ('negotiation', 'Negociación', 4, 'normal', 80),
            ('won', 'Ganada', 5, 'won', 100),
            ('lost', 'Perdida', 6, 'lost', 0)
        ) AS v(key, name, position, stage_type, probability)
    """)


def downgrade() -> None:
    op.drop_index("ix_opportunity_stages_tenant_id", table_name="opportunity_stages")
    op.drop_table("opportunity_stages")
