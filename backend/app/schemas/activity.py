from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ActivityType = Literal["call", "email", "meeting", "task"]
ActivityStatus = Literal["pending", "completed", "cancelled"]


class SaveActivityRequest(BaseModel):
    client_id: str
    opportunity_id: str | None = None
    owner_user_id: str
    activity_type: ActivityType
    title: str = Field(min_length=3, max_length=140)
    description: str | None = Field(default=None, max_length=1000)
    scheduled_at: datetime

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None


class UpdateActivityStatusRequest(BaseModel):
    status: ActivityStatus


class ActivityResponse(BaseModel):
    id: str
    client_id: str
    client_name: str
    opportunity_id: str | None
    opportunity_name: str | None
    owner_user_id: str
    owner_name: str
    activity_type: ActivityType
    title: str
    description: str | None
    scheduled_at: datetime
    status: ActivityStatus
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
