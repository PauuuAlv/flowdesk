from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CreateOpportunityStageRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    stage_type: Literal["normal", "won", "lost"] = "normal"
    default_probability: int = Field(ge=0, le=100)
    position: int = Field(ge=1, le=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class UpdateOpportunityStageRequest(CreateOpportunityStageRequest):
    is_active: bool


class OpportunityStageResponse(BaseModel):
    id: str
    key: str
    name: str
    stage_type: Literal["normal", "won", "lost"]
    default_probability: int
    position: int
    is_active: bool
    created_at: datetime
