import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.permissions import (
    ADMIN_ROLE_KEY,
    PERMISSION_CATALOG,
    PERMISSION_CODES,
    ROLE_TEMPLATES,
)
from app.models.role import Permission, Role, RolePermission
from app.models.user import User
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


def build_role_permissions(role: Role, codes) -> list[RolePermission]:
    """Construye las filas role_permissions de un rol (siempre con su tenant_id)."""
    return [
        RolePermission(tenant_id=role.tenant_id, permission_code=code)
        for code in dict.fromkeys(codes)
    ]


def create_default_roles(db: Session, tenant_id: uuid.UUID) -> dict[str, Role]:
    """Crea los roles por defecto (Administrador, Miembro, Visor) de un tenant
    recién creado. Devuelve un dict {template_key: Role}. No hace commit."""
    roles: dict[str, Role] = {}
    for template in ROLE_TEMPLATES:
        role = Role(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=template["name"],
            description=template["description"],
            origin="template",
            template_key=template["key"],
            is_protected=template["is_protected"],
        )
        role.permissions = build_role_permissions(role, template["permissions"])
        db.add(role)
        roles[template["key"]] = role
    db.flush()
    return roles


def get_template_role(db: Session, tenant_id: uuid.UUID, template_key: str) -> Role | None:
    return (
        db.query(Role)
        .filter(Role.tenant_id == tenant_id, Role.template_key == template_key)
        .first()
    )


def get_user_permission_codes(user: User) -> list[str]:
    """Los permisos de un usuario son exactamente los de su rol asignado."""
    if not user.assigned_role:
        return []
    return user.assigned_role.permission_codes


def count_active_admins(db: Session, tenant_id: uuid.UUID, exclude_user_id: uuid.UUID | None = None) -> int:
    query = (
        db.query(func.count(User.id))
        .join(Role, Role.id == User.role_id)
        .filter(
            User.tenant_id == tenant_id,
            User.status == "active",
            Role.template_key == ADMIN_ROLE_KEY,
        )
    )
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.scalar() or 0


def sync_permission_catalog(db: Session) -> None:
    """Idempotente. Asegura que la tabla `permissions` refleje el catálogo y
    que el rol Administrador de cada tenant tenga TODOS los permisos (por si se
    agregaron permisos nuevos en una versión posterior). Hace commit."""
    for code, module, description in PERMISSION_CATALOG:
        db.execute(
            insert(Permission)
            .values(code=code, module=module, description=description)
            .on_conflict_do_update(
                index_elements=[Permission.code],
                set_={"module": module, "description": description},
            )
        )

    admin_roles = db.execute(
        select(Role.id, Role.tenant_id).where(Role.template_key == ADMIN_ROLE_KEY)
    ).all()
    for role_id, tenant_id in admin_roles:
        for code in PERMISSION_CODES:
            db.execute(
                insert(RolePermission)
                .values(role_id=role_id, tenant_id=tenant_id, permission_code=code)
                .on_conflict_do_nothing()
            )
    db.commit()
