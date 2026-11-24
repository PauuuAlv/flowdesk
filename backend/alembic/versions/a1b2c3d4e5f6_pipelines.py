"""varios pipelines por empresa

Crea la tabla pipelines y liga a ella las etapas y las oportunidades. Cada
empresa recibe un pipeline predeterminado "Ventas" con sus etapas y
oportunidades actuales, así que no cambia nada de lo que ya existe.

El nombre de una etapa pasa a ser único por pipeline (antes, por empresa); la
clave sigue siendo única por empresa porque la usan Opportunity.stage y el
historial de etapas.

Revision ID: a1b2c3d4e5f6
Revises: ff7b8c9d0ea5
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "a1b2c3d4e5f6"
down_revision = "ff7b8c9d0ea5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pipelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_pipeline_tenant_name"),
    )
    op.create_index("ix_pipelines_tenant_id", "pipelines", ["tenant_id"])
    op.create_index(
        "uq_pipeline_tenant_default", "pipelines", ["tenant_id"], unique=True,
        postgresql_where=sa.text("is_default"),
    )

    # Un pipeline predeterminado por cada empresa que tenga etapas u oportunidades.
    op.execute(
        """
        INSERT INTO pipelines (id, tenant_id, name, description, position, is_default, is_active)
        SELECT gen_random_uuid(), t.tenant_id, 'Ventas', 'Pipeline principal de la empresa', 1, true, true
        FROM (
            SELECT tenant_id FROM opportunity_stages
            UNION SELECT tenant_id FROM opportunities
            UNION SELECT id FROM tenants
        ) AS t
        """
    )

    for table in ("opportunity_stages", "opportunities"):
        op.add_column(table, sa.Column("pipeline_id", UUID(as_uuid=True), nullable=True))
        op.execute(
            f"""
            UPDATE {table} AS x SET pipeline_id = p.id
            FROM pipelines AS p
            WHERE p.tenant_id = x.tenant_id AND p.is_default
            """
        )
        op.alter_column(table, "pipeline_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_pipeline", table, "pipelines", ["pipeline_id"], ["id"])
        op.create_index(f"ix_{table}_pipeline_id", table, ["pipeline_id"])

    op.drop_constraint("uq_opportunity_stage_tenant_name", "opportunity_stages", type_="unique")
    op.create_unique_constraint(
        "uq_opportunity_stage_pipeline_name", "opportunity_stages", ["pipeline_id", "name"]
    )


def downgrade():
    op.drop_constraint("uq_opportunity_stage_pipeline_name", "opportunity_stages", type_="unique")
    op.create_unique_constraint(
        "uq_opportunity_stage_tenant_name", "opportunity_stages", ["tenant_id", "name"]
    )
    for table in ("opportunities", "opportunity_stages"):
        op.drop_index(f"ix_{table}_pipeline_id", table_name=table)
        op.drop_constraint(f"fk_{table}_pipeline", table, type_="foreignkey")
        op.drop_column(table, "pipeline_id")
    op.drop_index("uq_pipeline_tenant_default", table_name="pipelines")
    op.drop_index("ix_pipelines_tenant_id", table_name="pipelines")
    op.drop_table("pipelines")
