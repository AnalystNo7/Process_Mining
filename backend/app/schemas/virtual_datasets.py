from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VirtualDatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    physical_dataset_id: int
    config: dict[str, Any] = Field(default_factory=dict)


class VirtualDatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    physical_dataset_id: int
    name: str
    description: str | None
    role_mapping_snapshot: dict[str, Any]
    sla_rules_snapshot: list[Any]
    config: dict[str, Any]
    cached_stats: dict[str, Any] | None
    created_by: int
    created_at: datetime
    is_personal: bool


class VirtualDatasetBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    physical_dataset_id: int
    created_by: int
    created_at: datetime


class VirtualDatasetList(BaseModel):
    items: list[VirtualDatasetBrief]
    total: int


class BreakdownItem(BaseModel):
    name: str
    events: int
    cases: int


class RoleBreakdownResponse(BaseModel):
    role: str
    departments: list[BreakdownItem]
    total_events: int
    total_cases: int


class ActivityBreakdownResponse(BaseModel):
    activity_with_role: str
    operations: list[BreakdownItem]
    total_events: int
    total_cases: int
