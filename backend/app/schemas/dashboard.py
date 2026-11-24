from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class MoneyTotal(BaseModel):
    """Suma de importes de una sola moneda (nunca se mezclan monedas)."""
    currency: str
    amount: Decimal


class DashboardMetrics(BaseModel):
    # Moneda de la empresa: siempre es el primer total de cada lista.
    currency: str = "MXN"
    active_clients: int
    open_opportunities: int
    pipeline_value: list[MoneyTotal]
    weighted_pipeline_value: list[MoneyTotal]
    pending_activities: int
    overdue_activities: int
    pending_quotes: int
    accepted_quotes_value: list[MoneyTotal]


class PipelineStage(BaseModel):
    pipeline_id: str
    pipeline_name: str
    stage: str
    stage_name: str
    color: str
    count: int
    value: list[MoneyTotal]


class DashboardActivity(BaseModel):
    id: str
    title: str
    activity_type: str
    client_name: str
    scheduled_at: datetime
    is_overdue: bool


class DashboardQuote(BaseModel):
    id: str
    folio: str
    client_name: str
    total: Decimal
    currency: str
    status: str


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    pipeline: list[PipelineStage]
    upcoming_activities: list[DashboardActivity]
    recent_quotes: list[DashboardQuote]
