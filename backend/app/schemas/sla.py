from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SLAUnit = Literal["workdays", "calendar_days", "workhours", "hours"]


class SLARuleCreate(BaseModel):
    role: str = Field(min_length=1, max_length=255)
    operation_pattern: str = Field(default="*", min_length=1, max_length=500)
    sla_value: float = Field(gt=0)
    sla_unit: SLAUnit
    tolerance_hours: float = Field(default=0, ge=0)
    target_compliance_pct: float = Field(default=90.0, ge=0, le=100)
    effective_from: date
    effective_until: date | None = None
    description: str | None = None


class SLARuleUpdate(BaseModel):
    role: str | None = None
    operation_pattern: str | None = None
    sla_value: float | None = Field(default=None, gt=0)
    sla_unit: SLAUnit | None = None
    tolerance_hours: float | None = Field(default=None, ge=0)
    target_compliance_pct: float | None = Field(default=None, ge=0, le=100)
    effective_from: date | None = None
    effective_until: date | None = None
    description: str | None = None


class SLARuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    role: str
    operation_pattern: str
    sla_value: float
    sla_unit: str
    tolerance_hours: float
    target_compliance_pct: float
    effective_from: date
    effective_until: date | None
    description: str | None
    created_at: datetime


class SLARuleList(BaseModel):
    items: list[SLARuleResponse]
    total: int


class SLAComplianceRow(BaseModel):
    activity: str
    role: str
    total_events: int
    events_with_sla: int
    overdue_count: int
    compliance_pct: float | None
    target_pct: float
    status: str


class SLAComplianceResponse(BaseModel):
    rows: list[SLAComplianceRow]
    overall_compliance_pct: float | None
