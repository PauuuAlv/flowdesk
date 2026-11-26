from datetime import datetime

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    route: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int
    items: list[NotificationResponse]


class PushConfigResponse(BaseModel):
    enabled: bool
    public_key: str | None = None


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=16, max_length=255)
    auth: str = Field(min_length=8, max_length=255)


class PushSubscriptionRequest(BaseModel):
    """Forma de `PushSubscription.toJSON()` del navegador."""
    endpoint: str = Field(min_length=12, max_length=2048, pattern=r"^https://")
    keys: PushSubscriptionKeys
    expirationTime: float | None = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=12, max_length=2048)


class PushTestResponse(BaseModel):
    delivered: int
    removed: int
    failed: int
