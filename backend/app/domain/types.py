from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Event:
    """Одно событие журнала процесса."""

    case_id: str
    activity: str
    timestamp_start: datetime
    timestamp_end: datetime
    resource: str | None = None
    department: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventFilter:
    """Фильтр выборки событий.

    На уровне репозитория (SQL) применяются только событийные фильтры:
    date_range, departments, resources, activities, case_ids, attributes_filter.
    Кейс-уровневые (case_duration_range, with_rework) и roles применяются
    в pandas в доменной логике (см. domain/mining/filters.py, задача T24)."""

    date_range: tuple[datetime, datetime] | None = None
    departments: list[str] | None = None
    roles: list[str] | None = None
    resources: list[str] | None = None
    activities: list[str] | None = None
    case_duration_range: tuple[float, float] | None = None
    events_per_case_range: tuple[int, int] | None = None
    with_rework: bool | None = None
    attributes_filter: dict[str, list[str]] | None = None
    case_ids: list[str] | None = None
