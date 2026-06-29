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


def compute_case_duration_cdf(
    df: pd.DataFrame, sla_target_seconds: float | None = None
) -> dict[str, Any]:
    """Комбо-длительность №1: кривая накопления (CDF / Service Level Curve).

    Возвращает точки «X% кейсов завершились за ≤ N секунд». Для каждого кейса
    берётся полная длительность (compute_case_duration). Точки сортируются по
    возрастанию длительности, y = доля кейсов ≤ текущей (0..100).

    Если кейсов больше 500 — точки прорежаются до ~200 равномерных квантилей
    (крайние сохраняются), чтобы не раздувать JSON. Это прорежение визуальной
    кривой, статистики (перцентили, % в SLA) считаются по полному набору.

    sla_target_seconds: если задан — добавляется pct_within_sla (доля кейсов,
    уложившихся в норматив). Пустой df → points: [].
    """
    empty: dict[str, Any] = {
        "points": [],
        "percentiles": None,
        "sla_target_seconds": sla_target_seconds,
        "pct_within_sla": None,
        "x_label": "Длительность (сек)",
        "y_label": "% кейсов",
    }
    if df.empty:
        return empty

    cases = compute_case_duration(df)
    durations = np.sort(cases["duration_seconds"].to_numpy(dtype=float))
    n = durations.size
    if n == 0:
        return empty

    cum_pct = (np.arange(1, n + 1) / n) * 100.0

    # Прорежение для больших датасетов: ~200 равномерных индексов + крайние.
    if n > 500:
        idx = np.unique(
            np.concatenate(
                [[0], np.linspace(0, n - 1, 200).astype(int), [n - 1]]
            )
        )
    else:
        idx = np.arange(n)

    points = [
        {"x": float(durations[i]), "y": float(cum_pct[i])} for i in idx
    ]
    percentiles = {
        "p50": float(np.percentile(durations, 50)),
        "p90": float(np.percentile(durations, 90)),
        "p95": float(np.percentile(durations, 95)),
    }
    pct_within_sla: float | None = None
    if sla_target_seconds is not None:
        pct_within_sla = float((durations <= sla_target_seconds).mean() * 100.0)

    return {
        "points": points,
        "percentiles": percentiles,
        "sla_target_seconds": sla_target_seconds,
        "pct_within_sla": pct_within_sla,
        "x_label": "Длительность (сек)",
        "y_label": "% кейсов",
    }


def compute_duration_bottleneck_heatmap(
    df: pd.DataFrame,
    activity_col: str = "activity",
    dimension_col: str = "department",
    limit: int = 10,
    sort_by: str = "duration",
) -> dict[str, Any]:
    """Комбо-длительность №2: теплокарта узких мест.

    Матрица **операция (ось Y) × разрез (ось X, департамент/исполнитель)**;
    значение ячейки — МЕДИАНА собственной длительности операции
    (own_duration_sec, сек.) в этом разрезе.

    Показываются только топ-`limit` операций, ранжированных по `sort_by`:
    - "duration" — по медиане длительности (самые долгие операции);
    - "frequency" — по числу событий (самые частые операции).
    Операции возвращаются в `y_categories` в порядке ранга (первая — топ-1),
    разрезы — в `x_categories` (отсортированы по алфавиту). Фронт строит
    матрицу строго по этим спискам (без алфавитной пересортировки) и обрезает
    длинные подписи.

    Пустой df / нет нужных колонок → cells/categories пустые.
    """
    x_label = "Департамент" if dimension_col == "department" else "Исполнитель"
    y_label = "Операция"
    base = {
        "cells": [],
        "x_categories": [],
        "y_categories": [],
        "x_label": x_label,
        "y_label": y_label,
        "sort_by": sort_by,
    }
    needed = {activity_col, dimension_col, "own_duration_sec"}
    if df.empty or not needed.issubset(df.columns):
        return base

    work = df[[activity_col, dimension_col, "own_duration_sec"]].dropna(
        subset=[activity_col, dimension_col]
    )
    if work.empty:
        return base

    if sort_by == "frequency":
        ranked = work.groupby(activity_col).size().sort_values(ascending=False)
    else:
        ranked = (
            work.groupby(activity_col)["own_duration_sec"]
            .median()
            .sort_values(ascending=False)
        )
    top_activities = [str(a) for a in ranked.head(limit).index]

    sub = work[work[activity_col].astype(str).isin(top_activities)]
    grouped = sub.groupby([activity_col, dimension_col])["own_duration_sec"].median()
    cells = [
        {"x": str(dim), "y": str(activity), "value": float(median_sec)}
        for (activity, dim), median_sec in grouped.items()
    ]
    x_categories = sorted({str(d) for d in sub[dimension_col].unique()})
    return {
        "cells": cells,
        "x_categories": x_categories,
        "y_categories": top_activities,
        "x_label": x_label,
        "y_label": y_label,
        "sort_by": sort_by,
    }


def compute_sojourn_vs_own(
    df: pd.DataFrame, activity_col: str = "activity", limit: int = 15
) -> dict[str, Any]:
    """Комбо-длительность №3: работа vs ожидание по операциям.

    На каждую операцию: «работа» = медиана own_duration_sec; «ожидание» =
    медиана max(sojourn − own, 0), где sojourn — длительность с учётом простоя
    между событиями (compute_sojourn_time). Топ-`limit` операций по частоте.
    Пустой df → rows: [].
    """
    if df.empty or "own_duration_sec" not in df.columns:
        return {"rows": []}

    enriched = compute_sojourn_time(df)
    enriched = enriched.dropna(subset=[activity_col])
    if enriched.empty:
        return {"rows": []}

    own = enriched["own_duration_sec"].astype(float)
    wait = (enriched["sojourn_seconds"].astype(float) - own).clip(lower=0)
    work_df = pd.DataFrame(
        {activity_col: enriched[activity_col].to_numpy(), "own": own, "wait": wait}
    )

    counts = (
        work_df.groupby(activity_col).size().sort_values(ascending=False).head(limit)
    )
    rows: list[dict[str, Any]] = []
    for activity in counts.index:
        sub = work_df[work_df[activity_col] == activity]
        rows.append(
            {
                "activity": str(activity),
                "work_seconds": float(sub["own"].median()),
                "wait_seconds": float(sub["wait"].median()),
                "n": int(len(sub)),
            }
        )
    return {"rows": rows}
