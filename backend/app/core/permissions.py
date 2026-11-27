"""Catálogo global de permisos y plantillas de roles por defecto.

- `PERMISSION_CATALOG` es la fuente de verdad de los permisos que existen en el
  sistema. Se refleja en la tabla `permissions` (migración + sincronización al
  arrancar la API), así `role_permissions` siempre apunta a un permiso real.
- `ROLE_TEMPLATES` son los roles que se crean automáticamente para cada tenant
  nuevo. Cada tenant recibe SU PROPIA copia (tabla `roles` con su tenant_id):
  los roles de un tenant nunca son visibles ni utilizables por otro.
"""

# (código, módulo, descripción)
PERMISSION_CATALOG: tuple[tuple[str, str, str], ...] = (
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
    ("audit.view", "audit", "Ver la auditoría de la empresa"),
    ("audit.export", "audit", "Descargar el reporte de auditoría en PDF"),
)

PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _module, _description in PERMISSION_CATALOG)

ADMIN_ROLE_KEY = "admin"
MEMBER_ROLE_KEY = "member"
VIEWER_ROLE_KEY = "viewer"

ROLE_TEMPLATES = (
    {
        "key": ADMIN_ROLE_KEY,
        "name": "Administrador",
        "description": "Control completo de la configuración y operación de la empresa.",
        # Protegido: no se puede renombrar, eliminar ni quitarle permisos.
        # Siempre tiene TODOS los permisos del catálogo.
        "is_protected": True,
        "permissions": PERMISSION_CODES,
    },
    {
        "key": MEMBER_ROLE_KEY,
        "name": "Miembro",
        "description": "Acceso básico a los módulos operativos asignados.",
        "is_protected": False,
        "permissions": (
            "dashboard.view",
            "clients.view",
            "opportunities.view",
            "activities.view",
            "activities.create",
            "activities.update",
            "activities.complete",
            "quotes.view",
            "products.view",
        ),
    },
    {
        "key": VIEWER_ROLE_KEY,
        "name": "Visor",
        "description": "Solo consulta la información de la empresa, sin poder modificarla.",
        "is_protected": False,
        # La auditoría es información sensible: no se da por defecto al Visor.
        "permissions": tuple(
            code for code in PERMISSION_CODES if code.endswith(".view") and code != "audit.view"
        ),
    },
)
