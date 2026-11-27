"""Catálogo de permisos y roles por defecto de la ADMINISTRACIÓN DE PLATAFORMA.

Es independiente de los permisos de los tenants (app/core/permissions.py):
estos permisos los tienen las cuentas de ArmSystem que administran el SaaS
(tabla `platform_admins`), nunca los usuarios de una empresa.

- `PLATFORM_PERMISSION_CATALOG` se refleja en la tabla `platform_permissions`
  (migración + sincronización al arrancar la API).
- `PLATFORM_ROLE_TEMPLATES` son los roles que existen desde el inicio. Se
  pueden crear más roles personalizados desde la página "Equipo de plataforma".
"""

# (código, módulo, descripción)
PLATFORM_PERMISSION_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("platform.overview.view", "overview", "Ver el panel general de la plataforma"),
    ("platform.tenants.view", "tenants", "Ver empresas, su consumo y su detalle"),
    ("platform.tenants.create", "tenants", "Crear empresas e invitar a su administrador"),
    ("platform.tenants.update", "tenants", "Editar empresas, su plan, su suscripción y su estado"),
    ("platform.tenants.delete", "tenants", "Eliminar empresas y todos sus datos"),
    ("platform.plans.view", "plans", "Ver los planes y cuántas empresas tiene cada uno"),
    ("platform.subscriptions.view", "subscriptions", "Ver solicitudes de cambio de plan"),
    ("platform.subscriptions.resolve", "subscriptions", "Aprobar o rechazar solicitudes de cambio de plan"),
    ("platform.audit.view", "audit", "Consultar la bitácora de auditoría"),
    ("platform.audit.export", "audit", "Descargar el reporte de auditoría en PDF"),
    ("platform.team.view", "team", "Ver el equipo de plataforma"),
    ("platform.team.invite", "team", "Invitar integrantes al equipo de plataforma"),
    ("platform.team.update", "team", "Cambiar el rol de un integrante o activarlo/desactivarlo"),
    ("platform.roles.view", "roles", "Ver los roles y permisos de plataforma"),
    ("platform.roles.create", "roles", "Crear roles de plataforma"),
    ("platform.roles.update", "roles", "Editar roles de plataforma"),
    ("platform.roles.delete", "roles", "Eliminar roles de plataforma"),
)

PLATFORM_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _m, _d in PLATFORM_PERMISSION_CATALOG)

SUPERADMIN_ROLE_KEY = "superadmin"
OPERATOR_ROLE_KEY = "operator"
VIEWER_ROLE_KEY = "viewer"

PLATFORM_ROLE_TEMPLATES = (
    {
        "key": SUPERADMIN_ROLE_KEY,
        "name": "Superadministrador",
        "description": "Control total de la plataforma, del equipo y de sus roles.",
        # Protegido: no se puede renombrar, eliminar ni quitarle permisos.
        "is_protected": True,
        "permissions": PLATFORM_PERMISSION_CODES,
    },
    {
        "key": OPERATOR_ROLE_KEY,
        "name": "Operador",
        "description": "Administra empresas, planes y suscripciones, sin gestionar al equipo.",
        "is_protected": False,
        "permissions": (
            "platform.overview.view",
            "platform.tenants.view",
            "platform.tenants.create",
            "platform.tenants.update",
            "platform.plans.view",
            "platform.subscriptions.view",
            "platform.subscriptions.resolve",
            "platform.audit.view",
            "platform.team.view",
        ),
    },
    {
        "key": VIEWER_ROLE_KEY,
        "name": "Consulta",
        "description": "Solo consulta la información de la plataforma, sin poder modificarla.",
        "is_protected": False,
        "permissions": tuple(code for code in PLATFORM_PERMISSION_CODES if code.endswith(".view")),
    },
)
