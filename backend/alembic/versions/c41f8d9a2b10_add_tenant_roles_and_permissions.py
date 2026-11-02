"""add tenant roles and permissions

Revision ID: c41f8d9a2b10
Revises: 5eec3cffeb30
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c41f8d9a2b10"
down_revision: Union[str, None] = "5eec3cffeb30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("template_key", sa.String(length=50), nullable=True),
        sa.Column("is_protected", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )
    op.create_index(op.f("ix_roles_tenant_id"), "roles", ["tenant_id"])
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_code", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_code"),
    )
    op.add_column("users", sa.Column("role_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"])
    op.create_foreign_key("fk_users_role_id", "users", "roles", ["role_id"], ["id"])

    op.execute(
        """
        INSERT INTO roles
            (id, tenant_id, name, description, origin, template_key, is_protected)
        SELECT gen_random_uuid(), id, 'Administrador',
               'Control completo de la configuración y operación de la empresa.',
               'template', 'admin', true
        FROM tenants
        UNION ALL
        SELECT gen_random_uuid(), id, 'Supervisor',
               'Consulta la operación y administra clientes sin cambiar la configuración.',
               'template', 'supervisor', false
        FROM tenants
        UNION ALL
        SELECT gen_random_uuid(), id, 'Miembro',
               'Acceso básico a los módulos operativos asignados.',
               'template', 'member', false
        FROM tenants
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permission_code
        FROM roles
        CROSS JOIN LATERAL unnest(
            CASE roles.template_key
                WHEN 'admin' THEN ARRAY[
                    'dashboard.view','users.view','users.invite','users.update','users.delete',
                    'roles.view','roles.create','roles.update','roles.delete',
                    'clients.view','clients.create','clients.update','clients.delete'
                ]
                WHEN 'supervisor' THEN ARRAY[
                    'dashboard.view','users.view','clients.view','clients.create','clients.update'
                ]
                ELSE ARRAY['dashboard.view','clients.view']
            END
        ) AS permission_code
        WHERE roles.origin = 'template'
        """
    )
    op.execute(
        """
        UPDATE users
        SET role_id = roles.id
        FROM roles
        WHERE roles.tenant_id = users.tenant_id
          AND roles.template_key = CASE WHEN users.role = 'admin' THEN 'admin' ELSE 'member' END
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_role_id", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_column("users", "role_id")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_roles_tenant_id"), table_name="roles")
    op.drop_table("roles")
