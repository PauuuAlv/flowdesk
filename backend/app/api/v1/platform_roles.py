"""Roles y permisos del equipo de administración de plataforma."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.platform_permissions import PLATFORM_PERMISSION_CODES
from app.models.platform_admin import PlatformAdmin
from app.models.platform_audit import PlatformAuditLog
from app.models.platform_role import PlatformPermission, PlatformRole
from app.schemas.platform_role import (
    PlatformPermissionResponse,
    PlatformRoleResponse,
    SavePlatformRoleRequest,
)
from app.security.platform_admin_auth import require_platform_permission
from app.services.platform_access import build_platform_role_permissions

router = APIRouter()


def _role_or_404(db: Session, role_id: uuid.UUID) -> PlatformRole:
    role = db.query(PlatformRole).filter(PlatformRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform role not found")
    return role


def _ensure_unique_permissions(db: Session, codes, exclude_role_id=None) -> None:
    """Evita dos roles con exactamente el mismo acceso y distinto nombre."""
    target = set(codes)
    query = db.query(PlatformRole)
    if exclude_role_id:
        query = query.filter(PlatformRole.id != exclude_role_id)
    for existing in query.all():
        if set(existing.permission_codes) == target:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "duplicate_permissions", "role_name": existing.name},
            )


def _serialize(db: Session, role: PlatformRole) -> PlatformRoleResponse:
    member_count = (
        db.query(func.count(PlatformAdmin.id)).filter(PlatformAdmin.role_id == role.id).scalar() or 0
    )
    return PlatformRoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        origin=role.origin,
        template_key=role.template_key,
        is_protected=role.is_protected,
        member_count=member_count,
        permissions=role.permission_codes,
    )


@router.get("/permissions", response_model=list[PlatformPermissionResponse])
def list_platform_permissions(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.roles.view")),
):
    items = db.query(PlatformPermission).order_by(PlatformPermission.module, PlatformPermission.code).all()
    return [PlatformPermissionResponse(code=p.code, module=p.module, description=p.description) for p in items]


@router.get("", response_model=list[PlatformRoleResponse])
def list_platform_roles(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.roles.view")),
):
    roles = db.query(PlatformRole).order_by(PlatformRole.origin.desc(), PlatformRole.name.asc()).all()
    return [_serialize(db, role) for role in roles]


@router.get("/{role_id}", response_model=PlatformRoleResponse)
def get_platform_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.roles.view")),
):
    return _serialize(db, _role_or_404(db, role_id))


@router.post("", response_model=PlatformRoleResponse, status_code=status.HTTP_201_CREATED)
def create_platform_role(
    payload: SavePlatformRoleRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.roles.create")),
):
    _ensure_unique_permissions(db, payload.permissions)
    role = PlatformRole(
        name=payload.name,
        description=payload.description,
        origin="custom",
        template_key=None,
        is_protected=False,
    )
    role.permissions = build_platform_role_permissions(payload.permissions)
    db.add(role)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform role name already exists")
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_role.created",
        description=f"Se creó el rol de plataforma {role.name}.",
        details={"role_id": str(role.id), "permissions": payload.permissions},
    ))
    db.commit()
    db.refresh(role)
    return _serialize(db, role)


@router.patch("/{role_id}", response_model=PlatformRoleResponse)
def update_platform_role(
    role_id: uuid.UUID,
    payload: SavePlatformRoleRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.roles.update")),
):
    role = _role_or_404(db, role_id)
    # Nadie puede modificar el rol que tiene asignado (evita auto-otorgarse permisos).
    if role.id == admin.role_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot edit your own role")
    # Superadministrador siempre tiene todos los permisos; no se compara.
    if not role.is_protected:
        _ensure_unique_permissions(db, payload.permissions, exclude_role_id=role.id)
    before = role.permission_codes

    # Los roles por defecto conservan su nombre (se identifican por template_key).
    if role.origin != "template":
        role.name = payload.name
    role.description = payload.description
    # Superadministrador siempre tiene TODOS los permisos: si se le pudieran
    # quitar, la plataforma podría quedarse sin nadie capaz de administrarla.
    codes = PLATFORM_PERMISSION_CODES if role.is_protected else payload.permissions
    role.permissions = build_platform_role_permissions(codes)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform role name already exists")
    after = role.permission_codes
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_role.updated",
        description=f"Se actualizó el rol de plataforma {role.name}.",
        details={
            "role_id": str(role.id),
            "added": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
        },
    ))
    db.commit()
    db.refresh(role)
    return _serialize(db, role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.roles.delete")),
):
    role = _role_or_404(db, role_id)
    if role.origin == "template":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Default platform role cannot be deleted")
    if db.query(PlatformAdmin).filter(PlatformAdmin.role_id == role.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform role is assigned to members")
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_role.deleted",
        description=f"Se eliminó el rol de plataforma {role.name}.",
        details={"role_id": str(role.id)},
    ))
    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
