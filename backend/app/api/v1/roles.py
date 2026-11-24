import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PERMISSION_CODES
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.access_control import (
    PermissionResponse,
    SaveRoleRequest,
    TenantRoleResponse,
)
from app.security.permissions import require_permission
from app.services.access_control import build_role_permissions

router = APIRouter()


def _role_or_404(db: Session, tenant_id, role_id: uuid.UUID) -> Role:
    # Siempre filtrado por el tenant del token: un tenant nunca ve roles de otro.
    role = db.query(Role).filter(Role.id == role_id, Role.tenant_id == tenant_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _ensure_unique_permissions(db: Session, tenant_id, codes, exclude_role_id=None) -> None:
    """Evita dos roles con exactamente el mismo acceso y distinto nombre."""
    target = set(codes)
    query = db.query(Role).filter(Role.tenant_id == tenant_id)
    if exclude_role_id:
        query = query.filter(Role.id != exclude_role_id)
    for existing in query.all():
        if set(existing.permission_codes) == target:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "duplicate_permissions", "role_name": existing.name},
            )


def _serialize_role(db: Session, role: Role) -> TenantRoleResponse:
    user_count = (
        db.query(func.count(User.id))
        .filter(User.role_id == role.id, User.tenant_id == role.tenant_id)
        .scalar()
        or 0
    )
    return TenantRoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        origin=role.origin,
        template_key=role.template_key,
        is_protected=role.is_protected,
        user_count=user_count,
        permissions=role.permission_codes,
    )


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("roles.view")),
):
    """Catálogo global de permisos del sistema (tabla `permissions`)."""
    permissions = db.query(Permission).order_by(Permission.module.asc(), Permission.code.asc()).all()
    return [
        PermissionResponse(code=p.code, module=p.module, description=p.description)
        for p in permissions
    ]


@router.get("", response_model=list[TenantRoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.view")),
):
    roles = (
        db.query(Role)
        .filter(Role.tenant_id == current_user.tenant_id)
        .order_by(Role.origin.desc(), Role.name.asc())
        .all()
    )
    return [_serialize_role(db, role) for role in roles]


@router.post("", response_model=TenantRoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: SaveRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.create")),
):
    _ensure_unique_permissions(db, current_user.tenant_id, payload.permissions)
    role = Role(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        origin="custom",
        template_key=None,
        is_protected=False,
    )
    role.permissions = build_role_permissions(role, payload.permissions)
    db.add(role)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    db.refresh(role)
    return _serialize_role(db, role)


@router.get("/{role_id}", response_model=TenantRoleResponse)
def get_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.view")),
):
    return _serialize_role(db, _role_or_404(db, current_user.tenant_id, role_id))


@router.patch("/{role_id}", response_model=TenantRoleResponse)
def update_role(
    role_id: uuid.UUID,
    payload: SaveRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.update")),
):
    role = _role_or_404(db, current_user.tenant_id, role_id)
    # Nadie puede modificar el rol que tiene asignado (evita auto-otorgarse permisos).
    if role.id == current_user.role_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot edit your own role")
    # El rol protegido siempre tiene todos los permisos; no se compara.
    if not role.is_protected:
        _ensure_unique_permissions(db, current_user.tenant_id, payload.permissions, exclude_role_id=role.id)

    # Los roles por defecto conservan su nombre (se identifican por template_key).
    if role.origin != "template":
        role.name = payload.name.strip()
    role.description = payload.description.strip()

    # El Administrador siempre tiene todos los permisos: si se le pudieran
    # quitar, la empresa podría quedarse sin nadie capaz de administrarla.
    codes = PERMISSION_CODES if role.is_protected else payload.permissions
    role.permissions = build_role_permissions(role, codes)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    db.refresh(role)
    return _serialize_role(db, role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.delete")),
):
    role = _role_or_404(db, current_user.tenant_id, role_id)
    if role.origin == "template":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Default role cannot be deleted")
    if db.query(User).filter(User.role_id == role.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role is assigned to users")
    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
