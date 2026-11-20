PLAN_TEMPLATES = {
    "basic": {
        "name": "Básico",
        "max_users": 5,
        "max_clients": 100,
        "max_products": 100,
        "features": ["CRM comercial", "Cotizaciones", "Catálogo de productos", "Roles y permisos"],
    },
    "professional": {
        "name": "Profesional",
        "max_users": 20,
        "max_clients": 1000,
        "max_products": 1000,
        "features": ["Todo lo del plan Básico", "Mayor capacidad", "Roles personalizados", "Soporte prioritario"],
    },
    "enterprise": {
        "name": "Empresarial",
        "max_users": 500,
        "max_clients": 50000,
        "max_products": 50000,
        "features": ["Todo lo del plan Profesional", "Capacidad empresarial", "Administración avanzada", "Atención especializada"],
    },
}


def get_plan(plan_key: str) -> dict:
    return PLAN_TEMPLATES[plan_key]
