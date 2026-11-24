"""Roles y permisos del equipo de administración de plataforma."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.platform_permissions import (
    PLATFORM_PERMISSION_CATALOG,
    PLATFORM_PERMISSION_CODES,
    PLATFORM_ROLE_TEMPLATES,
    SUPERADMIN_ROLE_KEY,
)
from app.models.platform_admin import PlatformAdmin
from app.models.platform_role import PlatformPermission, PlatformRole, PlatformRolePermission


def build_platform_role_permissions(codes) -> list[PlatformRolePermission]:
    return [PlatformRolePermission(permission_code=code) for code in dict.fromkeys(codes)]


def get_platform_template_role(db: Session, template_key: str) -> PlatformRole | None:
    return db.query(PlatformRole).filter(PlatformRole.template_key == template_key).first()


def count_active_superadmins(db: Session, exclude_admin_id: uuid.UUID | None = None) -> int:
    """Cuenta las cuentas activas (con contraseña definida) con rol Superadministrador."""
    query = (
        db.query(func.count(PlatformAdmin.id))
        .join(PlatformRole, PlatformRole.id == PlatformAdmin.role_id)
        .filter(
            PlatformRole.template_key == SUPERADMIN_ROLE_KEY,
            PlatformAdmin.is_active.is_(True),
            PlatformAdmin.hashed_password.isnot(None),
        )
    )
    if exclude_admin_id:
        query = query.filter(PlatformAdmin.id != exclude_admin_id)
    return query.scalar() or 0


def sync_platform_access(db: Session) -> None:
    """Idempotente. Mantiene `platform_permissions` alineada con el catálogo,
    crea los roles por defecto que falten y garantiza que Superadministrador
    tenga TODOS los permisos. Hace commit."""
    for code, module, description in PLATFORM_PERMISSION_CATALOG:
        db.execute(
            insert(PlatformPermission)
            .values(code=code, module=module, description=description)
            .on_conflict_do_update(
                index_elements=[PlatformPermission.code],
                set_={"module": module, "description": description},
            )
        )
    db.flush()

    for template in PLATFORM_ROLE_TEMPLATES:
        if get_platform_template_role(db, template["key"]):
            continue
        role = PlatformRole(
            name=template["name"],
            description=template["description"],
            origin="template",
            template_key=template["key"],
            is_protected=template["is_protected"],
        )
        role.permissions = build_platform_role_permissions(template["permissions"])
        db.add(role)
    db.flush()

    superadmin_id = db.execute(
        select(PlatformRole.id).where(PlatformRole.template_key == SUPERADMIN_ROLE_KEY)
    ).scalar()
    if superadmin_id:
        for code in PLATFORM_PERMISSION_CODES:
            db.execute(
                insert(PlatformRolePermission)
                .values(role_id=superadmin_id, permission_code=code)
                .on_conflict_do_nothing()
            )
        mark_platform_owner(db, superadmin_id)
    db.commit()


def mark_platform_owner(db: Session, superadmin_role_id: uuid.UUID) -> None:
    """La cuenta con SUPERADMIN_EMAIL (.env) es la cuenta principal: siempre
    Superadministrador y activa. Si cambia el correo del .env, la marca pasa a
    la nueva cuenta (cuando exista). No hace commit."""
    owner_email = (settings.SUPERADMIN_EMAIL or "").strip().lower()
    if not owner_email:
        return
    db.query(PlatformAdmin).filter(
        PlatformAdmin.is_owner.is_(True), func.lower(PlatformAdmin.email) != owner_email
    ).update({PlatformAdmin.is_owner: False}, synchronize_session=False)
    owner = db.query(PlatformAdmin).filter(func.lower(PlatformAdmin.email) == owner_email).first()
    if owner:
        owner.is_owner = True
        owner.is_active = True
        owner.role_id = superadmin_role_id
