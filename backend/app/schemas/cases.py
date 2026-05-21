from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CaseSummary(BaseModel):
    case_id: str
    n_events: int
    n_unique_activities: int
    duration_seconds: float
    has_rework: bool
    start: datetime
    end: datetime


class CaseListResponse(BaseModel):
    items: list[CaseSummary]
    total: int
    page: int
    page_size: int


class CaseEvent(BaseModel):
    activity: str
    timestamp_start: datetime
    timestamp_end: datetime
    resource: str | None
    department: str | None
    role: str | None
    sojourn_seconds: float
    is_repeat: bool


class CaseDetailResponse(BaseModel):
    case_id: str
    attributes: dict[str, Any]
    events: list[CaseEvent]
    total_duration_seconds: float
    has_rework: bool
    n_events: int
