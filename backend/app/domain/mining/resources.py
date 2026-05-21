"""Анализ исполнителей (см. 02_DOMAIN_LOGIC.md)."""

import pandas as pd


def compute_resource_workload(df: pd.DataFrame) -> pd.DataFrame:
    """Нагрузка исполнителей: resource | n_cases | n_events |
    avg_own_duration_seconds | n_unique_activities. Сортировка по n_events убыв."""
    empty = pd.DataFrame(
        columns=[
            "resource",
            "n_cases",
            "n_events",
            "avg_own_duration_seconds",
            "n_unique_activities",
        ]
    )
    if len(df) == 0 or df["resource"].dropna().empty:
        return empty

    work = df.copy()
    if "own_duration_sec" not in work.columns:
        work["own_duration_sec"] = (
            work["timestamp_end"] - work["timestamp_start"]
        ).dt.total_seconds()

    return (
        work.dropna(subset=["resource"])
        .groupby("resource")
        .agg(
            n_cases=("case_id", "nunique"),
            n_events=("activity", "count"),
            avg_own_duration_seconds=("own_duration_sec", "mean"),
            n_unique_activities=("activity", "nunique"),
        )
        .reset_index()
        .sort_values("n_events", ascending=False)
        .reset_index(drop=True)
    )
