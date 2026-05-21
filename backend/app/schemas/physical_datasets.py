from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnInfo(BaseModel):
    name: str
    sample_values: list[str]
    dtype: str


class PreviewResponse(BaseModel):
    columns: list[ColumnInfo]
    preview_rows: list[dict[str, Any]]
    total_rows: int
    suggested_mapping: dict[str, str]
    preview_token: str


class PhysicalDatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    preview_token: str
    column_mapping: dict[str, Any]
    save_as_template: bool = False


class UploadTaskResponse(BaseModel):
    id: int
    status: str
    task_id: str | None


class PhysicalDatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    file_name: str
    file_size_bytes: int
    status: str
    total_events: int
    total_cases: int
    unique_activities: int
    period_start: datetime | None
    period_end: datetime | None
    health_status: str
    health_report: dict[str, Any]
    column_mapping: dict[str, Any]
    uploaded_at: datetime
    error_message: str | None


class PhysicalDatasetList(BaseModel):
    items: list[PhysicalDatasetResponse]
    total: int


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None
    error: str | None = None


class HealthCheckItem(BaseModel):
    name: str
    severity: str
    message: str
    value: Any


class HealthReportResponse(BaseModel):
    status: str
    checks: list[HealthCheckItem]
