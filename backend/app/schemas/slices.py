from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SliceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


class SliceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    filters: dict[str, Any] | None = None


class SliceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    virtual_dataset_id: int
    name: str
    description: str | None
    filters: dict[str, Any]
    created_by: int
    created_at: datetime
    updated_at: datetime


class SliceList(BaseModel):
    items: list[SliceResponse]
    total: int
