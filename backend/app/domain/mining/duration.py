"""Метрики длительности операций и кейсов (см. 02_DOMAIN_LOGIC.md)."""

from typing import Any

import numpy as np
import pandas as pd


def compute_own_duration(df: pd.DataFrame) -> pd.Series:
    """Собственная длительность операции = timestamp_end - timestamp_start (сек)."""
    return (df["timestamp_end"] - df["timestamp_start"]).dt.total_seconds()


def compute_sojourn_time(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет колонку sojourn_seconds — длительность с учётом перехода.

    Для события: sojourn = timestamp_end - timestamp_end предыдущего события
    в кейсе. Для первого события кейса = собственная длительность.
    Сортировка внутри кейса — по timestamp_end, затем timestamp_start."""
    result = df.sort_values(
        ["case_id", "timestamp_end", "timestamp_start"]
    ).reset_index(drop=True)
    result["prev_end"] = result.groupby("case_id")["timestamp_end"].shift(1)
    result["sojourn_seconds"] = (
        result["timestamp_end"] - result["prev_end"]
    ).dt.total_seconds()

    first_mask = result["prev_end"].isna()
    result.loc[first_mask, "sojourn_seconds"] = (
        result.loc[first_mask, "timestamp_end"]
        - result.loc[first_mask, "timestamp_start"]
    ).dt.total_seconds()

    return result.drop(columns=["prev_end"])


def compute_case_duration(df: pd.DataFrame) -> pd.DataFrame:
    """Длительность кейса: case_id, start, end, duration_seconds, n_events,
    n_unique_activities."""
    return (
        df.groupby("case_id")
        .agg(
            start=("timestamp_start", "min"),
            end=("timestamp_end", "max"),
            n_events=("activity", "count"),
            n_unique_activities=("activity", "nunique"),
        )
        .assign(
            duration_seconds=lambda x: (x["end"] - x["start"]).dt.total_seconds()
        )
        .reset_index()
    )


def compute_operation_durations_boxplot(
    df: pd.DataFrame, activity_col: str = "activity", limit: int = 15
) -> dict[str, Any]:
    """T45: распределение длительности операций для виджета «ящик с усами».

    Возвращает `{'traces': [...]}` — список словарей по топ-`limit` операциям,
    отсортированных по частоте (`n_events`) убыванию. Для каждой операции:
        name   — название операции (значение `activity_col`);
        y      — массив длительностей (own_duration_sec, сек.), Plotly из него
                 рисует ящик, усы и точки-выбросы;
        n      — число событий операции;
        q1, median, q3, mean, min, max — статистики (на случай, если фронт
                 захочет показать в подсказке без пересчёта).
    Пустой df или отсутствующая колонка `own_duration_sec` → {'traces': []}.
    """
    if df.empty or "own_duration_sec" not in df.columns:
        return {"traces": []}

    durations = df[[activity_col, "own_duration_sec"]].dropna()
    if durations.empty:
        return {"traces": []}

    counts = (
        durations.groupby(activity_col).size().sort_values(ascending=False).head(limit)
    )

    traces: list[dict[str, Any]] = []
    for activity in counts.index:
        values = durations.loc[
            durations[activity_col] == activity, "own_duration_sec"
        ].to_numpy(dtype=float)
        if values.size == 0:
            continue
        traces.append(
            {
                "name": str(activity),
                "y": values.tolist(),
                "n": int(values.size),
                "q1": float(np.percentile(values, 25)),
                "median": float(np.percentile(values, 50)),
                "q3": float(np.percentile(values, 75)),
                "mean": float(values.mean()),
                "min": float(values.min()),
                "max": float(values.max()),
            }
        )
    return {"traces": traces}
