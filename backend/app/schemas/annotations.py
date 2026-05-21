from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AnnotationTargetType = Literal["node", "edge", "case", "time_range"]

# Обязательные ключи объекта target для каждого типа (см. T36).
_REQUIRED_TARGET_KEYS: dict[str, set[str]] = {
    "node": {"activity"},
    "edge": {"from", "to"},
    "case": {"case_id"},
    "time_range": {"start_date", "end_date"},
}


class AnnotationCreate(BaseModel):
    target_type: AnnotationTargetType
    target: dict[str, Any]
    text: str = Field(min_length=1)
    color: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _validate_target(self) -> "AnnotationCreate":
        required = _REQUIRED_TARGET_KEYS[self.target_type]
        missing = required - set(self.target)
        if missing:
            raise ValueError(
                f"target для типа {self.target_type} требует ключи "
                f"{sorted(required)}, отсутствуют {sorted(missing)}"
            )
        return self


class AnnotationUpdate(BaseModel):
    text: str = Field(min_length=1)


class AnnotationResponse(BaseModel):
    id: int
    virtual_dataset_id: int
    target_type: str
    target: dict[str, Any]
    text: str
    color: str | None
    author_id: int
    author_name: str
    created_at: datetime
    updated_at: datetime


class AnnotationList(BaseModel):
    items: list[AnnotationResponse]
    total: int
