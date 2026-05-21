"""Drill-down по кейсам — список кейсов и детальная трасса (см. T32)."""

from typing import Any

import pandas as pd

from app.core.exceptions import EntityNotFoundError
from app.domain.mining.duration import compute_case_duration, compute_sojourn_time
from app.domain.mining.rework import split_cases_by_rework


def _clean(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value)


def list_cases(
    df: pd.DataFrame, page: int = 1, page_size: int = 50
) -> tuple[list[dict[str, Any]], int]:
    """Список кейсов с базовой статистикой, отсортированный по длительности."""
    if len(df) == 0:
        return [], 0
    case_dur = compute_case_duration(df).sort_values(
        "duration_seconds", ascending=False
    )
    with_rework, _ = split_cases_by_rework(df)
    total = len(case_dur)
    page_slice = case_dur.iloc[(page - 1) * page_size : page * page_size]
    rows = [
        {
            "case_id": str(row["case_id"]),
            "n_events": int(row["n_events"]),
            "n_unique_activities": int(row["n_unique_activities"]),
            "duration_seconds": float(row["duration_seconds"]),
            "has_rework": str(row["case_id"]) in with_rework,
            "start": row["start"],
            "end": row["end"],
        }
        for _, row in page_slice.iterrows()
    ]
    return rows, total


def case_detail(df: pd.DataFrame, case_id: str) -> dict[str, Any]:
    """Полная трасса кейса с длительностями и пометками повторов."""
    case_df = df[df["case_id"] == case_id]
    if len(case_df) == 0:
        raise EntityNotFoundError(f"Кейс {case_id!r} не найден")

    sojourn_df = compute_sojourn_time(case_df)
    seen: set[str] = set()
    events: list[dict[str, Any]] = []
    for _, row in sojourn_df.iterrows():
        activity = str(row["activity"])
        events.append(
            {
                "activity": activity,
                "timestamp_start": row["timestamp_start"],
                "timestamp_end": row["timestamp_end"],
                "resource": _clean(row.get("resource")),
                "department": _clean(row.get("department")),
                "role": _clean(row.get("role")),
                "sojourn_seconds": float(row["sojourn_seconds"]),
                "is_repeat": activity in seen,
            }
        )
        seen.add(activity)

    first_attrs = case_df.iloc[0].get("attributes")
    total_duration = (
        case_df["timestamp_end"].max() - case_df["timestamp_start"].min()
    ).total_seconds()
    return {
        "case_id": case_id,
        "attributes": first_attrs if isinstance(first_attrs, dict) else {},
        "events": events,
        "total_duration_seconds": float(total_duration),
        "has_rework": len(seen) < len(events),
        "n_events": len(events),
    }
