from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ActivityType = Literal["call", "email", "meeting", "task"]
ActivityStatus = Literal["pending", "completed", "cancelled"]

# Anticipación máxima de un recordatorio: 30 días.
MAX_REMINDER_MINUTES = 30 * 24 * 60
MAX_REMINDERS = 10


class ActivityReminderInput(BaseModel):
    """Recordatorio enviado por el formulario. Con `id` se modifica; sin él se crea.

    Exactamente uno: `minutes_before` (X tiempo antes de la actividad) o
    `fixed_at` (fecha y hora exacta).
    """
    id: str | None = None
    minutes_before: int | None = Field(default=None, ge=0, le=MAX_REMINDER_MINUTES)
    fixed_at: datetime | None = None

    @model_validator(mode="after")
    def exactly_one_mode(self):
        if (self.minutes_before is None) == (self.fixed_at is None):
            raise ValueError("Indica minutes_before o fixed_at, no ambos")
        if self.fixed_at is not None and self.fixed_at.tzinfo is None:
            raise ValueError("fixed_at debe incluir zona horaria")
        return self


class ActivityReminderResponse(BaseModel):
    id: str
    minutes_before: int | None
    fixed_at: datetime | None
    remind_at: datetime
    sent_at: datetime | None


class SaveActivityRequest(BaseModel):
    client_id: str
    opportunity_id: str | None = None
    owner_user_id: str
    activity_type: ActivityType
    title: str = Field(min_length=3, max_length=140)
    description: str | None = Field(default=None, max_length=1000)
    scheduled_at: datetime
    # None = no tocar los recordatorios; lista = conjunto completo (los que
    # falten se eliminan). Así clientes anteriores no los borran por accidente.
    reminders: list[ActivityReminderInput] | None = Field(default=None, max_length=MAX_REMINDERS)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None


class UpdateActivityRemindersRequest(BaseModel):
    """Conjunto completo de recordatorios de una actividad (los que falten se eliminan)."""
    reminders: list[ActivityReminderInput] = Field(default_factory=list, max_length=MAX_REMINDERS)


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
    reminders: list[ActivityReminderResponse] = []
    created_at: datetime
    updated_at: datetime
