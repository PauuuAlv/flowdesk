import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PERMISSION_CODES
from app.models.role import Role, RolePermission
from app.models.user import User
from app.schemas.access_control import (
    PermissionResponse,
    SaveRoleRequest,
    TenantRoleResponse,
)
from app.security.permissions import require_permission

router = APIRouter()


def _role_or_404(db: Session, tenant_id, role_id: uuid.UUID) -> Role:
    role = db.query(Role).filter(Role.id == role_id, Role.tenant_id == tenant_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _serialize_role(db: Session, role: Role) -> TenantRoleResponse:
    user_count = db.query(func.count(User.id)).filter(User.role_id == role.id).scalar() or 0
    return TenantRoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        origin=role.origin,
        is_protected=role.is_protected,
        user_count=user_count,
        permissions=sorted(item.permission_code for item in role.permissions),
    )


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    _user: User = Depends(require_permission("roles.view")),
):
    return [PermissionResponse(code=code) for code in PERMISSION_CODES]


@router.get("", response_model=list[TenantRoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.view")),
):
    roles = (
        db.query(Role)
        .filter(Role.tenant_id == current_user.tenant_id)
        .order_by(Role.name.asc())
        .all()
    )
    return [_serialize_role(db, role) for role in roles]


@router.post("", response_model=TenantRoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: SaveRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.create")),
):
    role = Role(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        origin="custom",
        is_protected=False,
        permissions=[RolePermission(permission_code=code) for code in payload.permissions],
    )
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
    if not role.is_protected:
        role.name = payload.name.strip()
    role.description = payload.description.strip()
    role.permissions = [RolePermission(permission_code=code) for code in payload.permissions]
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
    if role.is_protected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Protected role cannot be deleted")
    if db.query(User).filter(User.role_id == role.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role is assigned to users")
    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
