"""color por etapa de oportunidad

Agrega opportunity_stages.color (#rrggbb). Las etapas existentes reciben un
color de la paleta según su orden dentro de su pipeline; las de cierre ganado
quedan en verde y las de cierre perdido en rojo.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

# Igual que STAGE_PALETTE en app/services/pipelines.py.
PALETTE = ("#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899", "#14b8a6", "#6366f1", "#f97316")


def upgrade():
    op.add_column(
        "opportunity_stages",
        sa.Column("color", sa.String(7), nullable=False, server_default="#3b82f6"),
    )
    palette = "ARRAY[" + ", ".join(f"'{c}'" for c in PALETTE) + "]"
    op.execute(
        f"""
        UPDATE opportunity_stages AS s SET color = ({palette})[((o.n - 1) % {len(PALETTE)}) + 1]
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY pipeline_id ORDER BY position, name) AS n
            FROM opportunity_stages WHERE stage_type = 'normal'
        ) AS o
        WHERE o.id = s.id
        """
    )
    op.execute("UPDATE opportunity_stages SET color = '#22c55e' WHERE stage_type = 'won'")
    op.execute("UPDATE opportunity_stages SET color = '#ef4444' WHERE stage_type = 'lost'")
    op.create_check_constraint("ck_opportunity_stages_color", "opportunity_stages", "color ~ '^#[0-9a-f]{6}$'")


def downgrade():
    op.drop_constraint("ck_opportunity_stages_color", "opportunity_stages", type_="check")
    op.drop_column("opportunity_stages", "color")
