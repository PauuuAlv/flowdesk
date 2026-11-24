"""roles y permisos del equipo de plataforma

- Crea `platform_permissions` (catálogo), `platform_roles` y
  `platform_role_permissions`.
- Crea los roles por defecto: Superadministrador (protegido, todos los
  permisos), Operador y Consulta.
- `platform_admins.role_id` reemplaza al texto `platform_admins.role`
  ('superadmin' -> Superadministrador, 'viewer' -> Consulta).

Revision ID: fb2d3e4f5a61
Revises: fa1c2d3e4f50
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "fb2d3e4f5a61"
down_revision = "fa1c2d3e4f50"
branch_labels = None
depends_on = None

# Copia congelada del catálogo al momento de esta migración.
PERMISSIONS = (
    ("platform.overview.view", "overview", "Ver el panel general de la plataforma"),
    ("platform.tenants.view", "tenants", "Ver empresas, su consumo y su detalle"),
    ("platform.tenants.create", "tenants", "Crear empresas e invitar a su administrador"),
    ("platform.tenants.update", "tenants", "Editar empresas, su plan, su suscripción y su estado"),
    ("platform.tenants.delete", "tenants", "Eliminar empresas y todos sus datos"),
    ("platform.plans.view", "plans", "Ver los planes y cuántas empresas tiene cada uno"),
    ("platform.subscriptions.view", "subscriptions", "Ver solicitudes de cambio de plan"),
    ("platform.subscriptions.resolve", "subscriptions", "Aprobar o rechazar solicitudes de cambio de plan"),
    ("platform.audit.view", "audit", "Consultar la bitácora de auditoría"),
    ("platform.team.view", "team", "Ver el equipo de plataforma"),
    ("platform.team.invite", "team", "Invitar integrantes al equipo de plataforma"),
    ("platform.team.update", "team", "Cambiar el rol de un integrante o activarlo/desactivarlo"),
    ("platform.roles.view", "roles", "Ver los roles y permisos de plataforma"),
    ("platform.roles.create", "roles", "Crear roles de plataforma"),
    ("platform.roles.update", "roles", "Editar roles de plataforma"),
    ("platform.roles.delete", "roles", "Eliminar roles de plataforma"),
)
ALL_CODES = [code for code, _m, _d in PERMISSIONS]
ROLES = (
    ("superadmin", "Superadministrador", "Control total de la plataforma, del equipo y de sus roles.", True, ALL_CODES),
    ("operator", "Operador", "Administra empresas, planes y suscripciones, sin gestionar al equipo.", False, [
        "platform.overview.view", "platform.tenants.view", "platform.tenants.create",
        "platform.tenants.update", "platform.plans.view", "platform.subscriptions.view",
        "platform.subscriptions.resolve", "platform.audit.view", "platform.team.view",
    ]),
    ("viewer", "Consulta", "Solo consulta la información de la plataforma, sin poder modificarla.", False,
     [code for code in ALL_CODES if code.endswith(".view")]),
)


def upgrade():
    op.create_table(
        "platform_permissions",
        sa.Column("code", sa.String(80), primary_key=True),
        sa.Column("module", sa.String(40), nullable=False),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_platform_permissions_module", "platform_permissions", ["module"])
    op.create_table(
        "platform_roles",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("template_key", sa.String(50), nullable=True, unique=True),
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "platform_role_permissions",
        sa.Column("role_id", sa.UUID(), sa.ForeignKey("platform_roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "permission_code", sa.String(80),
            sa.ForeignKey("platform_permissions.code", ondelete="CASCADE"), primary_key=True,
        ),
    )

    permissions_table = sa.table(
        "platform_permissions", sa.column("code"), sa.column("module"), sa.column("description")
    )
    op.bulk_insert(permissions_table, [dict(code=c, module=m, description=d) for c, m, d in PERMISSIONS])

    roles_table = sa.table(
        "platform_roles", sa.column("id", sa.UUID()), sa.column("name"), sa.column("description"),
        sa.column("origin"), sa.column("template_key"), sa.column("is_protected"),
    )
    role_permissions_table = sa.table(
        "platform_role_permissions", sa.column("role_id", sa.UUID()), sa.column("permission_code")
    )
    role_ids = {}
    for key, name, description, protected, codes in ROLES:
        role_ids[key] = uuid.uuid4()
        op.bulk_insert(roles_table, [dict(
            id=role_ids[key], name=name, description=description, origin="template",
            template_key=key, is_protected=protected,
        )])
        op.bulk_insert(role_permissions_table, [dict(role_id=role_ids[key], permission_code=c) for c in codes])

    # platform_admins.role (texto) -> platform_admins.role_id
    op.add_column("platform_admins", sa.Column("role_id", sa.UUID(), nullable=True))
    op.execute(sa.text(
        "UPDATE platform_admins SET role_id = CASE WHEN role = 'superadmin' THEN :superadmin ELSE :viewer END"
    ).bindparams(
        sa.bindparam("superadmin", role_ids["superadmin"], type_=sa.UUID()),
        sa.bindparam("viewer", role_ids["viewer"], type_=sa.UUID()),
    ))
    op.alter_column("platform_admins", "role_id", nullable=False)
    op.create_index("ix_platform_admins_role_id", "platform_admins", ["role_id"])
    op.create_foreign_key(
        "fk_platform_admins_role", "platform_admins", "platform_roles", ["role_id"], ["id"]
    )
    op.drop_column("platform_admins", "role")


def downgrade():
    op.add_column(
        "platform_admins", sa.Column("role", sa.String(30), nullable=False, server_default="viewer")
    )
    op.execute(
        "UPDATE platform_admins a SET role = 'superadmin' FROM platform_roles r "
        "WHERE r.id = a.role_id AND r.template_key = 'superadmin'"
    )
    op.alter_column("platform_admins", "role", server_default=None)
    op.drop_constraint("fk_platform_admins_role", "platform_admins", type_="foreignkey")
    op.drop_index("ix_platform_admins_role_id", table_name="platform_admins")
    op.drop_column("platform_admins", "role_id")
    op.drop_table("platform_role_permissions")
    op.drop_table("platform_roles")
    op.drop_index("ix_platform_permissions_module", table_name="platform_permissions")
    op.drop_table("platform_permissions")
