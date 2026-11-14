from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    active_clients: int
    open_opportunities: int
    pipeline_value: Decimal
    weighted_pipeline_value: Decimal
    pending_activities: int
    overdue_activities: int
    pending_quotes: int
    accepted_quotes_value: Decimal


class PipelineStage(BaseModel):
    stage: str
    count: int
    value: Decimal


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
    status: str


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    pipeline: list[PipelineStage]
    upcoming_activities: list[DashboardActivity]
    recent_quotes: list[DashboardQuote]
