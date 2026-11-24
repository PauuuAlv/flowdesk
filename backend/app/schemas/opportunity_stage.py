from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CreateOpportunityStageRequest(BaseModel):
    # Pipeline al que pertenece la etapa (no cambia después de crearla).
    pipeline_id: str
    name: str = Field(min_length=2, max_length=80)
    stage_type: Literal["normal", "won", "lost"] = "normal"
    default_probability: int = Field(ge=0, le=100)
    position: int = Field(ge=1, le=20)
    # Color base #rrggbb; sin indicarlo se asigna uno de la paleta.
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value: str | None) -> str | None:
        return value.lower() if value else None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class UpdateOpportunityStageRequest(CreateOpportunityStageRequest):
    pipeline_id: str | None = None
    is_active: bool


class OpportunityStageResponse(BaseModel):
    id: str
    pipeline_id: str
    key: str
    name: str
    stage_type: Literal["normal", "won", "lost"]
    default_probability: int
    position: int
    color: str
    is_active: bool
    created_at: datetime
