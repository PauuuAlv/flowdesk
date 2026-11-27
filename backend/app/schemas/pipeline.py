from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PipelinePayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=200)
    # Sin indicarlo se conserva (al editar) o se asigna uno de la paleta (al crear).
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value: str | None) -> str | None:
        return value.lower() if value else None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        value = " ".join(value.split()) if value else None
        return value or None


class CreatePipelineRequest(PipelinePayload):
    # Copiar las etapas de otro pipeline; sin indicarlo se usan las predeterminadas.
    copy_stages_from: str | None = None


class UpdatePipelineRequest(PipelinePayload):
    is_active: bool
    is_default: bool


class PipelineResponse(BaseModel):
    id: str
    name: str
    description: str | None
    position: int
    is_default: bool
    is_active: bool
    color: str
    stage_count: int
    open_opportunities: int
    total_opportunities: int
    created_at: datetime
