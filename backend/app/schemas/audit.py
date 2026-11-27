from datetime import datetime

from pydantic import BaseModel


class AuditEntryResponse(BaseModel):
    id: str
    created_at: datetime
    operation: str  # CREATE | UPDATE | DELETE | EVENT
    action: str
    description: str
    entity: str | None
    entity_label: str | None
    entity_id: str | None
    actor_type: str  # user | platform_admin | system
    actor_id: str | None
    actor_email: str | None
    ip_address: str | None
    user_agent: str | None
    http_method: str | None
    endpoint: str | None
    before_data: dict | None
    after_data: dict | None
    details: dict
    tenant_id: str | None = None
    tenant_name: str | None = None


class AuditPageResponse(BaseModel):
    items: list[AuditEntryResponse]
    total: int
    page: int
    page_size: int


class AuditFilterOption(BaseModel):
    value: str
    label: str


class AuditFiltersResponse(BaseModel):
    entities: list[AuditFilterOption]
    actors: list[AuditFilterOption]
