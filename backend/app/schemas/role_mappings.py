from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: int
    name: str
    mapping: dict[str, str]
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class RoleMappingUpdate(BaseModel):
    mapping: dict[str, str]
    roles: list[str]


class SuggestRequest(BaseModel):
    departments: list[str]
    physical_dataset_id: int | None = None


class SuggestionItem(BaseModel):
    role: str
    matched_pattern: str | None


class SuggestResponse(BaseModel):
    suggestions: dict[str, SuggestionItem]
    available_roles: list[str]


class RoleMappingHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    name: str
    created_at: datetime
