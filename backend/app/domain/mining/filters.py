"""Применение фильтров к журналу событий (см. 02_DOMAIN_LOGIC.md)."""

from datetime import datetime
from typing import Any

import pandas as pd

from app.domain.mining.duration import compute_case_duration
from app.domain.mining.rework import split_cases_by_rework
from app.domain.types import EventFilter

_SECONDS_PER_DAY = 86400.0


def parse_filters(data: dict[str, Any] | None) -> EventFilter:
    """Преобразует JSON-описание фильтра (формат named_slices / dashboard
    global_filters) в доменный EventFilter."""
    if not data:
        return EventFilter()

    date_range: tuple[datetime, datetime] | None = None
    raw_range = data.get("date_range")
    if raw_range and raw_range.get("from") and raw_range.get("to"):
        date_range = (
            datetime.fromisoformat(raw_range["from"]),
            datetime.fromisoformat(raw_range["to"]),
        )

    case_duration_range: tuple[float, float] | None = None
    raw_duration = data.get("case_duration")
    if raw_duration:
        min_days = float(raw_duration.get("min_days", 0))
        max_days = float(raw_duration.get("max_days", 10**6))
        case_duration_range = (min_days * _SECONDS_PER_DAY, max_days * _SECONDS_PER_DAY)

    events_per_case_range: tuple[int, int] | None = None
    raw_events = data.get("events_per_case")
    if raw_events:
        min_events = int(raw_events.get("min", 0))
        max_events = int(raw_events.get("max", 10**9))
        events_per_case_range = (min_events, max_events)

    return EventFilter(
        date_range=date_range,
        departments=data.get("departments"),
        roles=data.get("roles"),
        resources=data.get("resources"),
        activities=data.get("activities"),
        case_duration_range=case_duration_range,
        events_per_case_range=events_per_case_range,
        with_rework=data.get("with_rework"),
        attributes_filter=data.get("attributes_filter"),
        case_ids=data.get("case_ids"),
    )


def apply_filter(df: pd.DataFrame, event_filter: EventFilter) -> pd.DataFrame:
    """Применяет фильтр к event log.

    Фильтры case_duration_range и with_rework — на уровне кейса: если кейс
    проходит фильтр, остаются ВСЕ его события (трасса не рвётся)."""
    result = df

    if event_filter.date_range is not None:
        start, end = event_filter.date_range
        result = result[
            (result["timestamp_start"] >= start) & (result["timestamp_start"] <= end)
        ]
    if event_filter.departments:
        result = result[result["department"].isin(event_filter.departments)]
    if event_filter.roles and "role" in result.columns:
        result = result[result["role"].isin(event_filter.roles)]
    if event_filter.resources:
        result = result[result["resource"].isin(event_filter.resources)]
    if event_filter.activities:
        result = result[result["activity"].isin(event_filter.activities)]
    if event_filter.case_ids:
        result = result[result["case_id"].isin(event_filter.case_ids)]
    if event_filter.attributes_filter:
        for key, values in event_filter.attributes_filter.items():
            result = result[
                result["attributes"].apply(
                    lambda attrs, k=key, v=values: isinstance(attrs, dict)
                    and attrs.get(k) in v
                )
            ]

    # Кейс-уровневые фильтры.
    if (
        event_filter.with_rework is not None
        or event_filter.case_duration_range is not None
        or event_filter.events_per_case_range is not None
    ):
        if len(result) == 0:
            return result
        case_dur = compute_case_duration(result)
        with_rework_set, without_rework_set = split_cases_by_rework(result)

        if event_filter.with_rework is True:
            valid_cases = with_rework_set
        elif event_filter.with_rework is False:
            valid_cases = without_rework_set
        else:
            valid_cases = set(case_dur["case_id"])

        if event_filter.case_duration_range is not None:
            min_d, max_d = event_filter.case_duration_range
            mask = (case_dur["duration_seconds"] >= min_d) & (
                case_dur["duration_seconds"] <= max_d
            )
            valid_cases = valid_cases & set(case_dur[mask]["case_id"])

        if event_filter.events_per_case_range is not None:
            min_e, max_e = event_filter.events_per_case_range
            mask = (case_dur["n_events"] >= min_e) & (case_dur["n_events"] <= max_e)
            valid_cases = valid_cases & set(case_dur[mask]["case_id"])

        result = result[result["case_id"].isin(valid_cases)]

    return result
