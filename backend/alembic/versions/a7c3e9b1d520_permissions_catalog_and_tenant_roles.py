"""tabla de permisos, roles por defecto (Administrador, Miembro, Visor) y
role_permissions con tenant

- Crea `permissions` (catálogo global) y liga `role_permissions` a ella por FK.
- `role_permissions` guarda tenant_id con FK compuesta a roles(id, tenant_id).
- `users.role_id` pasa a ser obligatorio, con FK compuesta (mismo tenant), y se
  elimina la columna legacy `users.role` (causaba que la UI y la API no
  coincidieran: el string decía 'admin' pero el role_id apuntaba a Miembro).
- El rol por defecto "Supervisor" pasa a ser un rol personalizado del tenant y
  se agrega el rol por defecto "Visor".
- Crea la vista `tenant_role_permissions` (rol, descripción, permisos y tenant).

Revision ID: a7c3e9b1d520
Revises: f51c9f3e7d42
"""
from alembic import op
import sqlalchemy as sa

revision = "a7c3e9b1d520"
down_revision = "f51c9f3e7d42"
branch_labels = None
depends_on = None

# Copia congelada del catálogo al momento de esta migración.
PERMISSIONS = (
    ("dashboard.view", "dashboard", "Ver el resumen de inicio"),
    ("users.view", "users", "Ver integrantes de la empresa"),
    ("users.invite", "users", "Invitar usuarios"),
    ("users.update", "users", "Cambiar el rol de un usuario"),
    ("users.delete", "users", "Activar o desactivar usuarios"),
    ("roles.view", "roles", "Ver roles y permisos"),
    ("roles.create", "roles", "Crear roles"),
    ("roles.update", "roles", "Editar roles"),
    ("roles.delete", "roles", "Eliminar roles"),
    ("clients.view", "clients", "Ver clientes"),
    ("clients.create", "clients", "Crear clientes"),
    ("clients.update", "clients", "Editar clientes"),
    ("clients.delete", "clients", "Eliminar clientes"),
    ("opportunities.view", "opportunities", "Ver oportunidades"),
    ("opportunities.create", "opportunities", "Crear oportunidades"),
    ("opportunities.update", "opportunities", "Editar oportunidades"),
    ("opportunities.close", "opportunities", "Cerrar oportunidades"),
    ("opportunities.archive", "opportunities", "Archivar oportunidades"),
    ("activities.view", "activities", "Ver actividades"),
    ("activities.create", "activities", "Crear actividades"),
    ("activities.update", "activities", "Editar actividades"),
    ("activities.complete", "activities", "Completar actividades"),
    ("quotes.view", "quotes", "Ver cotizaciones"),
    ("quotes.create", "quotes", "Crear cotizaciones"),
    ("quotes.update", "quotes", "Editar cotizaciones"),
    ("quotes.status", "quotes", "Cambiar el estado de cotizaciones"),
    ("products.view", "products", "Ver productos y servicios"),
    ("products.create", "products", "Crear productos y servicios"),
    ("products.update", "products", "Editar productos y servicios"),
    ("products.delete", "products", "Desactivar productos y servicios"),
    ("settings.view", "settings", "Ver la configuración de la empresa"),
    ("settings.update", "settings", "Editar la configuración de la empresa"),
)
MEMBER_PERMISSIONS = (
    "dashboard.view", "clients.view", "opportunities.view", "activities.view",
    "activities.create", "activities.update", "activities.complete", "quotes.view", "products.view",
)
VIEWER_PERMISSIONS = tuple(code for code, _m, _d in PERMISSIONS if code.endswith(".view"))
VIEWER_DESCRIPTION = "Solo consulta la información de la empresa, sin poder modificarla."


def _array(codes) -> str:
    return "ARRAY[" + ",".join(f"'{code}'" for code in codes) + "]::varchar[]"


def _insert_default_role(key: str, name: str, description: str, protected: bool) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO roles (id, tenant_id, name, description, origin, template_key, is_protected)
            SELECT gen_random_uuid(), t.id, :name, :description, 'template', :key, :protected
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM roles r WHERE r.tenant_id = t.id AND r.template_key = :key
            )
            """
        ).bindparams(key=key, name=name, description=description, protected=protected)
    )


def _seed_template_permissions(key: str, codes) -> None:
    """Solo para roles por defecto recién creados (sin permisos todavía)."""
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, tenant_id, permission_code)
        SELECT r.id, r.tenant_id, unnest({_array(codes)}) FROM roles r
        WHERE r.template_key = '{key}'
          AND NOT EXISTS (SELECT 1 FROM role_permissions x WHERE x.role_id = r.id)
        ON CONFLICT DO NOTHING
        """
    )


def upgrade():
    conn = op.get_bind()

    # 1. Catálogo global de permisos.
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(80), primary_key=True),
        sa.Column("module", sa.String(40), nullable=False),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])
    op.bulk_insert(
        sa.table("permissions", sa.column("code"), sa.column("module"), sa.column("description")),
        [dict(code=c, module=m, description=d) for c, m, d in PERMISSIONS],
    )
    op.execute("DELETE FROM role_permissions WHERE permission_code NOT IN (SELECT code FROM permissions)")

    # 2. Roles por tenant.
    op.create_unique_constraint("uq_role_id_tenant", "roles", ["id", "tenant_id"])
    # "Supervisor" deja de ser rol por defecto: se conserva como rol personalizado.
    op.execute(
        "UPDATE roles SET origin = 'custom', template_key = NULL, is_protected = false "
        "WHERE template_key = 'supervisor'"
    )
    # Si un tenant ya tenía un rol personalizado "Visor", se convierte en el rol por defecto.
    op.execute(
        "UPDATE roles SET origin = 'template', template_key = 'viewer', is_protected = false "
        "WHERE lower(name) = 'visor' AND template_key IS NULL"
    )
    _insert_default_role(
        "admin", "Administrador",
        "Control completo de la configuración y operación de la empresa.", True,
    )
    _insert_default_role("member", "Miembro", "Acceso básico a los módulos operativos asignados.", False)
    _insert_default_role("viewer", "Visor", VIEWER_DESCRIPTION, False)
    op.create_unique_constraint("uq_role_tenant_template", "roles", ["tenant_id", "template_key"])

    # 3. role_permissions con tenant_id y llaves foráneas reales.
    op.add_column("role_permissions", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(
        "UPDATE role_permissions rp SET tenant_id = r.tenant_id FROM roles r WHERE r.id = rp.role_id"
    )
    op.alter_column("role_permissions", "tenant_id", nullable=False)
    op.create_index("ix_role_permissions_tenant_id", "role_permissions", ["tenant_id"])
    old_fks = conn.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'role_permissions'::regclass AND contype = 'f'"
        )
    ).scalars().all()
    for name in old_fks:
        op.drop_constraint(name, "role_permissions", type_="foreignkey")
    op.create_foreign_key(
        "fk_role_permissions_role_tenant", "role_permissions", "roles",
        ["role_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_role_permissions_permission", "role_permissions", "permissions",
        ["permission_code"], ["code"], ondelete="CASCADE",
    )

    # Administrador: siempre TODOS los permisos.
    op.execute(
        "INSERT INTO role_permissions (role_id, tenant_id, permission_code) "
        "SELECT r.id, r.tenant_id, p.code FROM roles r CROSS JOIN permissions p "
        "WHERE r.template_key = 'admin' ON CONFLICT DO NOTHING"
    )
    _seed_template_permissions("member", MEMBER_PERMISSIONS)
    _seed_template_permissions("viewer", VIEWER_PERMISSIONS)

    # 4. users: role_id es la única fuente de verdad.
    # Corrige usuarios cuyo string legacy decía 'admin' pero su role_id no.
    op.execute(
        """
        UPDATE users u SET role_id = r.id
        FROM roles r
        WHERE r.tenant_id = u.tenant_id AND r.template_key = 'admin'
          AND u.role = 'admin'
          AND NOT EXISTS (
              SELECT 1 FROM roles cur WHERE cur.id = u.role_id AND cur.template_key = 'admin'
          )
        """
    )
    # Usuarios sin rol (o con un rol de otro tenant) -> Miembro.
    op.execute(
        """
        UPDATE users u SET role_id = r.id
        FROM roles r
        WHERE r.tenant_id = u.tenant_id AND r.template_key = 'member'
          AND NOT EXISTS (
              SELECT 1 FROM roles cur WHERE cur.id = u.role_id AND cur.tenant_id = u.tenant_id
          )
        """
    )
    op.drop_constraint("fk_users_role_id", "users", type_="foreignkey")
    op.alter_column("users", "role_id", nullable=False)
    op.create_foreign_key(
        "fk_users_role_tenant", "users", "roles", ["role_id", "tenant_id"], ["id", "tenant_id"],
    )
    op.drop_column("users", "role")

    # 5. Vista de consulta: rol + descripción + permisos + tenant.
    op.execute(
        """
        CREATE VIEW tenant_role_permissions AS
        SELECT r.tenant_id,
               t.name AS tenant_name,
               r.id AS role_id,
               r.name AS role_name,
               r.description AS role_description,
               r.origin,
               r.template_key,
               COALESCE(
                   array_agg(rp.permission_code ORDER BY rp.permission_code)
                       FILTER (WHERE rp.permission_code IS NOT NULL),
                   ARRAY[]::varchar[]
               ) AS permissions
        FROM roles r
        JOIN tenants t ON t.id = r.tenant_id
        LEFT JOIN role_permissions rp ON rp.role_id = r.id AND rp.tenant_id = r.tenant_id
        GROUP BY r.tenant_id, t.name, r.id, r.name, r.description, r.origin, r.template_key
        """
    )


def downgrade():
    op.execute("DROP VIEW IF EXISTS tenant_role_permissions")

    op.add_column(
        "users", sa.Column("role", sa.String(50), nullable=False, server_default="member")
    )
    op.execute(
        "UPDATE users u SET role = 'admin' FROM roles r "
        "WHERE r.id = u.role_id AND r.template_key = 'admin'"
    )
    op.drop_constraint("fk_users_role_tenant", "users", type_="foreignkey")
    op.alter_column("users", "role_id", nullable=True)
    op.create_foreign_key("fk_users_role_id", "users", "roles", ["role_id"], ["id"])

    op.drop_constraint("fk_role_permissions_permission", "role_permissions", type_="foreignkey")
    op.drop_constraint("fk_role_permissions_role_tenant", "role_permissions", type_="foreignkey")
    op.create_foreign_key(
        "role_permissions_role_id_fkey", "role_permissions", "roles",
        ["role_id"], ["id"], ondelete="CASCADE",
    )
    op.drop_index("ix_role_permissions_tenant_id", table_name="role_permissions")
    op.drop_column("role_permissions", "tenant_id")

    op.drop_constraint("uq_role_tenant_template", "roles", type_="unique")
    op.drop_constraint("uq_role_id_tenant", "roles", type_="unique")

    op.drop_index("ix_permissions_module", table_name="permissions")
    op.drop_table("permissions")
