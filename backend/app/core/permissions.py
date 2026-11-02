PERMISSION_CODES = (
    "dashboard.view",
    "users.view",
    "users.invite",
    "users.update",
    "users.delete",
    "roles.view",
    "roles.create",
    "roles.update",
    "roles.delete",
    "clients.view",
    "clients.create",
    "clients.update",
    "clients.delete",
)

ROLE_TEMPLATES = (
    {
        "key": "admin",
        "name": "Administrador",
        "description": "Control completo de la configuración y operación de la empresa.",
        "is_protected": True,
        "permissions": PERMISSION_CODES,
    },
    {
        "key": "supervisor",
        "name": "Supervisor",
        "description": "Consulta la operación y administra clientes sin cambiar la configuración.",
        "is_protected": False,
        "permissions": (
            "dashboard.view",
            "users.view",
            "clients.view",
            "clients.create",
            "clients.update",
        ),
    },
    {
        "key": "member",
        "name": "Miembro",
        "description": "Acceso básico a los módulos operativos asignados.",
        "is_protected": False,
        "permissions": ("dashboard.view", "clients.view"),
    },
)
