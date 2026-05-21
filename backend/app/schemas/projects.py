from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class UserBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: UserBriefResponse
    created_at: datetime
    physical_datasets_count: int
    virtual_datasets_count: int
    dashboards_count: int


class ProjectList(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
