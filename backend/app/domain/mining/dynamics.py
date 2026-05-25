"""Динамика операций по времени (см. 02_DOMAIN_LOGIC.md).

Гранулярность задаётся одной буквой Pandas period freq: D (день), W (неделя),
M (месяц), Q (квартал). Время приводится к МСК до бакетизации, чтобы границы
бакетов совпадали с человеческими сутками/неделями."""

from typing import Literal

import pandas as pd

from app.domain.mining.duration import compute_sojourn_time

Granularity = Literal["D", "W", "M", "Q"]

_PERIOD_FREQ: dict[str, str] = {"D": "D", "W": "W-MON", "M": "M", "Q": "Q"}


def _to_msk_naive(series: pd.Series) -> pd.Series:
    return series.dt.tz_convert("Europe/Moscow").dt.tz_localize(None)


def _period_label(series: pd.Series, granularity: str) -> pd.Series:
    freq = _PERIOD_FREQ.get(granularity, "M")
    return _to_msk_naive(series).dt.to_period(freq).astype(str)


def compute_monthly_dynamics(
    df: pd.DataFrame, activity_filter: str | None = None
) -> pd.DataFrame:
    """Помесячная динамика для устаревшего эндпоинта /monthly-dynamics."""
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

    work["month"] = _period_label(work["timestamp_start"], "M")
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


def compute_operations_dynamics(df: pd.DataFrame, granularity: str = "M") -> pd.DataFrame:
    """Динамика числа операций по выбранной гранулярности: ``bucket | n_events |
    n_cases | events_per_case``. Используется виджетом «Динамика количества
    операций» (бар = n_events, линия = events_per_case)."""
    empty = pd.DataFrame(columns=["bucket", "n_events", "n_cases", "events_per_case"])
    if len(df) == 0:
        return empty

    work = df[["timestamp_start", "case_id", "activity"]].copy()
    work["bucket"] = _period_label(work["timestamp_start"], granularity)
    grouped = (
        work.groupby("bucket")
        .agg(n_events=("activity", "count"), n_cases=("case_id", "nunique"))
        .reset_index()
        .sort_values("bucket")
    )
    grouped["events_per_case"] = (
        grouped["n_events"] / grouped["n_cases"].where(grouped["n_cases"] > 0)
    ).round(2)
    return grouped


def compute_case_flow(df: pd.DataFrame, granularity: str = "M") -> pd.DataFrame:
    """Входящий и исходящий поток кейсов по гранулярности: для каждого
    бакета — число стартовавших и завершившихся кейсов, плюс накопительные
    суммы. Стартовое/конечное время кейса — min(timestamp_start) и
    max(timestamp_end) по событиям кейса."""
    cols = ["bucket", "started", "ended", "cum_started", "cum_ended"]
    if len(df) == 0:
        return pd.DataFrame(columns=cols)

    cases = df.groupby("case_id").agg(
        start=("timestamp_start", "min"), end=("timestamp_end", "max")
    )
    started = _period_label(cases["start"], granularity).value_counts().rename("started")
    ended = _period_label(cases["end"], granularity).value_counts().rename("ended")
    flow = pd.concat([started, ended], axis=1).fillna(0).astype(int)
    flow.index.name = "bucket"
    flow = flow.sort_index().reset_index()
    flow["cum_started"] = flow["started"].cumsum()
    flow["cum_ended"] = flow["ended"].cumsum()
    return flow[cols]


def compute_events_per_case_histogram(df: pd.DataFrame) -> pd.DataFrame:
    """Распределение числа событий в кейсе: events_in_case | n_cases."""
    empty = pd.DataFrame(columns=["events_in_case", "n_cases"])
    if len(df) == 0:
        return empty
    counts = df.groupby("case_id").size()
    hist = (
        counts.value_counts()
        .rename_axis("events_in_case")
        .reset_index(name="n_cases")
        .sort_values("events_in_case")
        .reset_index(drop=True)
    )
    return hist
