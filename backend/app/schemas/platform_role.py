from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.platform_permissions import PLATFORM_PERMISSION_CODES


class SavePlatformRoleRequest(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str = Field(min_length=10, max_length=160)
    permissions: list[str] = Field(min_length=1)

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, permissions: list[str]) -> list[str]:
        unique_permissions = list(dict.fromkeys(permissions))
        if set(unique_permissions) - set(PLATFORM_PERMISSION_CODES):
            raise ValueError("Unsupported platform permission codes")
        return unique_permissions


class PlatformRoleResponse(BaseModel):
    id: str
    name: str
    description: str
    origin: Literal["template", "custom"]
    template_key: str | None
    is_protected: bool
    member_count: int
    permissions: list[str]


class PlatformPermissionResponse(BaseModel):
    code: str
    module: str
    description: str
