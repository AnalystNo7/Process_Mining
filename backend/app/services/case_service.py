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


# T49: разрешённые поля для серверной сортировки. Защита от sql/column-инъекций.
_CASES_SORT_FIELDS: frozenset[str] = frozenset(
    {
        "case_id",
        "n_events",
        "n_unique_activities",
        "duration_seconds",
        "has_rework",
        "start",
        "end",
    }
)
_EVENTS_SORT_FIELDS: frozenset[str] = frozenset(
    {
        "case_id",
        "activity",
        "timestamp_start",
        "timestamp_end",
        "resource",
        "department",
        "own_duration_seconds",
    }
)


def list_cases(
    df: pd.DataFrame,
    page: int = 1,
    page_size: int = 50,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> tuple[list[dict[str, Any]], int]:
    """Список кейсов с базовой статистикой.

    Поведение сортировки (T49):
      * если sort_by ∈ _CASES_SORT_FIELDS — сортируем по нему;
      * иначе дефолт `duration_seconds desc` (обратная совместимость);
      * `sort_order='asc'` → ascending=True, иначе descending.
    """
    if len(df) == 0:
        return [], 0
    case_dur = compute_case_duration(df)
    with_rework, _ = split_cases_by_rework(df)
    # has_rework — производное поле; добавим в df, чтобы можно было по нему сортировать.
    case_dur = case_dur.assign(
        has_rework=case_dur["case_id"].astype(str).isin(with_rework)
    )

    sort_field = sort_by if sort_by in _CASES_SORT_FIELDS else "duration_seconds"
    ascending = sort_order == "asc"
    case_dur = case_dur.sort_values(sort_field, ascending=ascending, kind="mergesort")
    total = len(case_dur)
    page_slice = case_dur.iloc[(page - 1) * page_size : page * page_size]
    rows = [
        {
            "case_id": str(row["case_id"]),
            "n_events": int(row["n_events"]),
            "n_unique_activities": int(row["n_unique_activities"]),
            "duration_seconds": float(row["duration_seconds"]),
            "has_rework": bool(row["has_rework"]),
            "start": row["start"],
            "end": row["end"],
        }
        for _, row in page_slice.iterrows()
    ]
    return rows, total


def list_events(
    df: pd.DataFrame,
    page: int = 1,
    page_size: int = 50,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> tuple[list[dict[str, Any]], int]:
    """Постраничный список сырых событий датасета (T44, подвкладка «Датасет»).

    Сортировка (T49):
      * если sort_by ∈ _EVENTS_SORT_FIELDS — основная сортировка по нему;
        вторичный ключ `(case_id, timestamp_start)` для стабильности трасс;
      * без sort_by — дефолт `(case_id, timestamp_start, timestamp_end)`.
    """
    if len(df) == 0:
        return [], 0
    # own_duration_seconds — вычисляемое поле; добавим, чтобы по нему можно было
    # сортировать на бэке (фронту он тоже отдаётся в каждой строке).
    if "own_duration_seconds" not in df.columns:
        df = df.assign(
            own_duration_seconds=(df["timestamp_end"] - df["timestamp_start"])
            .dt.total_seconds()
        )
    if sort_by in _EVENTS_SORT_FIELDS:
        ascending = sort_order == "asc"
        ordered = df.sort_values(sort_by, ascending=ascending, kind="mergesort")
    else:
        ordered = df.sort_values(
            ["case_id", "timestamp_start", "timestamp_end"], kind="mergesort"
        )
    total = len(ordered)
    page_slice = ordered.iloc[(page - 1) * page_size : page * page_size]
    rows: list[dict[str, Any]] = []
    for _, row in page_slice.iterrows():
        start = row["timestamp_start"]
        end = row["timestamp_end"]
        own_duration = (end - start).total_seconds()
        rows.append(
            {
                "case_id": str(row["case_id"]),
                "activity": str(row["activity"]),
                "timestamp_start": start,
                "timestamp_end": end,
                "resource": _clean(row.get("resource")),
                "department": _clean(row.get("department")),
                "own_duration_seconds": float(own_duration),
            }
        )
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
