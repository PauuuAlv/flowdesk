from sqlalchemy.orm import Session

from app.core.permissions import ROLE_TEMPLATES
from app.models.role import Role, RolePermission


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
