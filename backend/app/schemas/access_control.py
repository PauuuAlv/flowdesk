from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.permissions import PERMISSION_CODES


class SaveRoleRequest(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str = Field(min_length=10, max_length=160)
    permissions: list[str] = Field(min_length=1)

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, permissions: list[str]) -> list[str]:
        unique_permissions = list(dict.fromkeys(permissions))
        invalid = set(unique_permissions) - set(PERMISSION_CODES)
        if invalid:
            raise ValueError("Unsupported permission codes")
        return unique_permissions


class TenantRoleResponse(BaseModel):
    id: str
    name: str
    description: str
    origin: Literal["template", "custom"]
    is_protected: bool
    user_count: int
    permissions: list[str]


class PermissionResponse(BaseModel):
    code: str


class UpdateMemberRoleRequest(BaseModel):
    role_id: str


class UpdateMemberStatusRequest(BaseModel):
    status: Literal["active", "inactive"]


class TenantMemberResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role_id: str
    role_name: str
    status: Literal["active", "pending", "inactive"]


class MessageResponse(BaseModel):
    message: str
