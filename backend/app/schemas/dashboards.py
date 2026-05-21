from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WidgetCreate(BaseModel):
    widget_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    local_filters: dict[str, Any] | None = None
    use_global_filters: bool = True
    grid_x: int = 0
    grid_y: int = 0
    grid_width: int = 4
    grid_height: int = 3


class WidgetUpdate(BaseModel):
    title: str | None = None
    config: dict[str, Any] | None = None
    local_filters: dict[str, Any] | None = None
    use_global_filters: bool | None = None
    grid_x: int | None = None
    grid_y: int | None = None
    grid_width: int | None = None
    grid_height: int | None = None


class WidgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dashboard_id: int
    widget_type: str
    title: str
    config: dict[str, Any]
    local_filters: dict[str, Any] | None
    use_global_filters: bool
    grid_x: int
    grid_y: int
    grid_width: int
    grid_height: int


class DashboardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    global_filters: dict[str, Any] = Field(default_factory=dict)
    applied_slice_id: int | None = None
    layout: list[Any] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    global_filters: dict[str, Any] | None = None
    applied_slice_id: int | None = None
    layout: list[Any] | None = None


class DashboardResponse(BaseModel):
    id: int
    virtual_dataset_id: int
    name: str
    description: str | None
    global_filters: dict[str, Any]
    applied_slice_id: int | None
    layout: list[Any]
    created_by: int
    created_at: datetime
    widgets: list[WidgetResponse]


class DashboardBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_by: int
    created_at: datetime


class DashboardList(BaseModel):
    items: list[DashboardBrief]
    total: int
