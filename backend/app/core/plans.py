PLAN_TEMPLATES = {
    "basic": {
        "name": "Básico",
        "max_users": 5,
        "max_clients": 100,
        "max_products": 100,
    },
    "professional": {
        "name": "Profesional",
        "max_users": 20,
        "max_clients": 1000,
        "max_products": 1000,
    },
    "enterprise": {
        "name": "Empresarial",
        "max_users": 500,
        "max_clients": 50000,
        "max_products": 50000,
    },
}


def get_plan(plan_key: str) -> dict:
    return PLAN_TEMPLATES[plan_key]
