"""audit control fields on every table and tenant audit log

- Todas las tablas reciben created_by / created_by_type / updated_by /
  updated_by_type (NOT NULL). Los registros existentes quedan como `system`
  (UUID 00000000-0000-0000-0000-000000000000).
- created_at / updated_at existen y son NOT NULL en todas las tablas.
- platform_audit_logs se amplía (IP, navegador, endpoint, antes/después) y
  pierde sus llaves foráneas para conservar el historial aunque se borre la
  empresa o la cuenta.
- Nueva tabla tenant_audit_logs (auditoría de los usuarios de cada empresa).

Revision ID: a0b1c2d3e4f5
Revises: 36979f1fc50a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "36979f1fc50a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_ID = sa.text("'00000000-0000-0000-0000-000000000000'::uuid")
SYSTEM_TYPE = sa.text("'system'")
SKIP_TABLES = {"alembic_version", "tenant_audit_logs"}
CONTROL_COLUMNS = ("created_by", "created_by_type", "updated_by", "updated_by_type")
NEW_PLATFORM_COLUMNS = (
    "actor_type", "actor_email", "operation", "entity", "entity_id", "before_data",
    "after_data", "ip_address", "user_agent", "http_method", "endpoint",
)


def _audit_log_columns():
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    return [
        sa.Column("actor_type", sa.String(20), nullable=False, server_default=SYSTEM_TYPE),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("operation", sa.String(10), nullable=False, server_default=sa.text("'EVENT'")),
        sa.Column("entity", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.String(120), nullable=True),
        sa.Column("before_data", jsonb, nullable=True),
        sa.Column("after_data", jsonb, nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("http_method", sa.String(10), nullable=True),
        sa.Column("endpoint", sa.String(255), nullable=True),
    ]


def _control_columns():
    return [
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False, server_default=SYSTEM_ID),
        sa.Column("created_by_type", sa.String(20), nullable=False, server_default=SYSTEM_TYPE),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False, server_default=SYSTEM_ID),
        sa.Column("updated_by_type", sa.String(20), nullable=False, server_default=SYSTEM_TYPE),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Campos de control en todas las tablas (no incluye vistas).
    for table in sorted(set(inspector.get_table_names()) - SKIP_TABLES):
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name in ("created_at", "updated_at"):
            if name not in existing:
                op.add_column(table, sa.Column(
                    name, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"),
                ))
            else:
                op.execute(f'UPDATE "{table}" SET "{name}" = now() WHERE "{name}" IS NULL')
                op.alter_column(table, name, nullable=False, server_default=sa.text("now()"))
        for column in _control_columns():
            if column.name not in existing:
                # NOT NULL + server_default: las filas existentes quedan como `system`.
                op.add_column(table, column)

    # 2) Ampliar platform_audit_logs.
    for fk in inspector.get_foreign_keys("platform_audit_logs"):
        op.drop_constraint(fk["name"], "platform_audit_logs", type_="foreignkey")
    for column in _audit_log_columns():
        op.add_column("platform_audit_logs", column)
    op.execute(
        """UPDATE platform_audit_logs l
        SET actor_type = 'platform_admin', actor_email = a.email,
            created_by = a.id, created_by_type = 'platform_admin',
            updated_by = a.id, updated_by_type = 'platform_admin'
        FROM platform_admins a WHERE a.id = l.platform_admin_id"""
    )
    # Conserva el nombre de la empresa en eventos viejos (por si luego se elimina).
    op.execute(
        """UPDATE platform_audit_logs l
        SET details = l.details || jsonb_build_object('tenant_name', t.name)
        FROM tenants t WHERE t.id = l.tenant_id AND NOT (l.details ? 'tenant_name')"""
    )
    op.create_index("ix_platform_audit_logs_created_at", "platform_audit_logs", ["created_at"])
    op.create_index("ix_platform_audit_logs_tenant_id", "platform_audit_logs", ["tenant_id"])
    op.create_index("ix_platform_audit_logs_platform_admin_id", "platform_audit_logs", ["platform_admin_id"])

    # 3) Auditoría de los usuarios de cada empresa (sin llaves foráneas).
    op.create_table(
        "tenant_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        *_audit_log_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        *_control_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_audit_logs_action", "tenant_audit_logs", ["action"])
    op.create_index("ix_tenant_audit_logs_user_id", "tenant_audit_logs", ["user_id"])
    op.create_index("ix_tenant_audit_logs_tenant_created", "tenant_audit_logs", ["tenant_id", "created_at"])
    op.create_index("ix_tenant_audit_logs_tenant_entity", "tenant_audit_logs", ["tenant_id", "entity"])


def downgrade() -> None:
    op.drop_table("tenant_audit_logs")

    op.drop_index("ix_platform_audit_logs_platform_admin_id", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_logs_tenant_id", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_logs_created_at", table_name="platform_audit_logs")
    for name in NEW_PLATFORM_COLUMNS:
        op.drop_column("platform_audit_logs", name)
    # Antes de restaurar las FKs, se limpian referencias a registros ya borrados.
    op.execute(
        "UPDATE platform_audit_logs SET tenant_id = NULL "
        "WHERE tenant_id IS NOT NULL AND tenant_id NOT IN (SELECT id FROM tenants)"
    )
    op.execute(
        "UPDATE platform_audit_logs SET platform_admin_id = NULL "
        "WHERE platform_admin_id IS NOT NULL AND platform_admin_id NOT IN (SELECT id FROM platform_admins)"
    )
    op.create_foreign_key(
        "platform_audit_logs_platform_admin_id_fkey", "platform_audit_logs", "platform_admins",
        ["platform_admin_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "platform_audit_logs_tenant_id_fkey", "platform_audit_logs", "tenants",
        ["tenant_id"], ["id"], ondelete="SET NULL",
    )

    inspector = sa.inspect(op.get_bind())
    for table in sorted(set(inspector.get_table_names()) - SKIP_TABLES):
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name in CONTROL_COLUMNS:
            if name in existing:
                op.drop_column(table, name)
    # Columnas de fecha que no existían antes de esta migración.
    for table in ("role_permissions", "platform_role_permissions"):
        op.drop_column(table, "created_at")
        op.drop_column(table, "updated_at")
    for table in ("permissions", "platform_permissions"):
        op.drop_column(table, "updated_at")
