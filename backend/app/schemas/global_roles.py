from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GlobalRoleTemplateCreate(BaseModel):
    role_name: str = Field(min_length=1, max_length=255)
    patterns: list[str] = Field(default_factory=list)
    sort_order: int = Field(default=100, ge=0)
    is_active: bool = True


class GlobalRoleTemplateUpdate(BaseModel):
    role_name: str | None = Field(default=None, min_length=1, max_length=255)
    patterns: list[str] | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class GlobalRoleTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_name: str
    patterns: list[str]
    sort_order: int
    is_active: bool
    updated_at: datetime


class GlobalRoleTemplateList(BaseModel):
    items: list[GlobalRoleTemplateResponse]
    total: int
