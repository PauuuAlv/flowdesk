from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

OpportunityStage = Literal["prospecting", "contact", "proposal", "negotiation", "won", "lost"]


class OpportunityPayload(BaseModel):
    client_id: str
    owner_user_id: str
    name: str = Field(min_length=3, max_length=140)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    stage: OpportunityStage
    probability: int = Field(ge=0, le=100)
    expected_close_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None


class SaveOpportunityRequest(OpportunityPayload):
    pass


class UpdateOpportunityStageRequest(BaseModel):
    stage: OpportunityStage


class OpportunityResponse(BaseModel):
    id: str
    client_id: str
    client_name: str
    owner_user_id: str
    owner_name: str
    name: str
    amount: Decimal
    stage: OpportunityStage
    probability: int
    expected_close_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class OpportunityAssigneeResponse(BaseModel):
    id: str
    name: str
