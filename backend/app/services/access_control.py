from sqlalchemy.orm import Session

from app.core.permissions import ROLE_TEMPLATES
from app.models.role import Role, RolePermission
from app.models.opportunity_stage import OpportunityStage
from app.models.product_catalog import MeasurementUnit


OPPORTUNITY_STAGE_TEMPLATES = (
    ("prospecting", "Prospecto", 1, "normal", 10),
    ("contact", "Contacto", 2, "normal", 30),
    ("proposal", "Propuesta", 3, "normal", 60),
    ("negotiation", "Negociación", 4, "normal", 80),
    ("won", "Ganada", 5, "won", 100),
    ("lost", "Perdida", 6, "lost", 0),
)


def create_opportunity_stage_templates(db: Session, tenant_id) -> None:
    for key, name, position, stage_type, probability in OPPORTUNITY_STAGE_TEMPLATES:
        db.add(OpportunityStage(
            tenant_id=tenant_id, key=key, name=name, position=position,
            stage_type=stage_type, default_probability=probability, is_active=True,
        ))
    db.flush()


PRODUCT_UNIT_TEMPLATES = (
    ("piece", "Pieza", "pza"), ("service", "Servicio", "serv"),
    ("hour", "Hora", "h"), ("day", "Día", "día"), ("month", "Mes", "mes"),
    ("license", "Licencia", "lic"), ("package", "Paquete", "paq"),
)


def create_product_catalog_templates(db: Session, tenant_id) -> None:
    for key, name, abbreviation in PRODUCT_UNIT_TEMPLATES:
        db.add(MeasurementUnit(tenant_id=tenant_id, key=key, name=name, abbreviation=abbreviation, is_active=True))
    db.flush()


def create_role_templates(db: Session, tenant_id) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for template in ROLE_TEMPLATES:
        role = Role(
            tenant_id=tenant_id,
            name=template["name"],
            description=template["description"],
            origin="template",
            template_key=template["key"],
            is_protected=template["is_protected"],
        )
        role.permissions = [
            RolePermission(permission_code=code) for code in template["permissions"]
        ]
        db.add(role)
        roles[template["key"]] = role
    db.flush()
    return roles


def get_user_permission_codes(user) -> list[str]:
    if user.assigned_role:
        return sorted(permission.permission_code for permission in user.assigned_role.permissions)
    # Compatibilidad para usuarios anteriores a la migración.
    if user.role == "admin":
        return sorted(
            permission
            for template in ROLE_TEMPLATES
            if template["key"] == "admin"
            for permission in template["permissions"]
        )
    return []
