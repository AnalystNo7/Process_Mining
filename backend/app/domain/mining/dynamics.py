"""Динамика операций по месяцам (см. 02_DOMAIN_LOGIC.md)."""

import pandas as pd

from app.domain.mining.duration import compute_sojourn_time


def compute_monthly_dynamics(
    df: pd.DataFrame, activity_filter: str | None = None
) -> pd.DataFrame:
    """Помесячная динамика: month | n_events | n_cases | avg_sojourn_seconds.

    Группировка по месяцу начала операции (МСК). Если задан activity_filter —
    считается только по этой операции (drill-down)."""
    empty = pd.DataFrame(columns=["month", "n_events", "n_cases", "avg_sojourn_seconds"])
    if len(df) == 0:
        return empty

    work = df.copy()
    if activity_filter is not None:
        work = work[work["activity"] == activity_filter]
    if len(work) == 0:
        return empty

    if "sojourn_seconds" not in work.columns:
        work = compute_sojourn_time(work)

    work["month"] = (
        work["timestamp_start"]
        .dt.tz_convert("Europe/Moscow")
        .dt.tz_localize(None)
        .dt.to_period("M")
        .astype(str)
    )
    return (
        work.groupby("month")
        .agg(
            n_events=("activity", "count"),
            n_cases=("case_id", "nunique"),
            avg_sojourn_seconds=("sojourn_seconds", "mean"),
        )
        .reset_index()
        .sort_values("month")
    )
