"""Метрики длительности операций и кейсов (см. 02_DOMAIN_LOGIC.md)."""

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
