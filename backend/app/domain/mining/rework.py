"""Анализ повторов операций — ping-pong (см. 02_DOMAIN_LOGIC.md)."""

import pandas as pd

from app.domain.mining.duration import compute_case_duration


def compute_rework_per_operation(
    df: pd.DataFrame, activity_col: str = "activity"
) -> pd.DataFrame:
    """Таблица повторов: activity | total | repeats | rework_pct.

    repeats = число повторных вхождений операции в кейс (cnt - 1).
    Сортировка по total убыв."""
    per_case_op = (
        df.groupby(["case_id", activity_col]).size().reset_index(name="cnt")
    )
    per_case_op["repeats"] = (per_case_op["cnt"] - 1).clip(lower=0)
    agg = (
        per_case_op.groupby(activity_col)
        .agg(total=("cnt", "sum"), repeats=("repeats", "sum"))
        .reset_index()
        .rename(columns={activity_col: "activity"})
    )
    agg["rework_pct"] = (agg["repeats"] / agg["total"] * 100).round(2)
    return agg.sort_values("total", ascending=False).reset_index(drop=True)


def compute_global_rework_pct(df: pd.DataFrame, activity_col: str = "activity") -> float:
    """Общий процент повторов по всему датасету."""
    rework_df = compute_rework_per_operation(df, activity_col)
    total = int(rework_df["total"].sum())
    repeats = int(rework_df["repeats"].sum())
    return round(repeats / total * 100, 2) if total > 0 else 0.0


def split_cases_by_rework(df: pd.DataFrame) -> tuple[set[str], set[str]]:
    """Возвращает (кейсы с повторами, кейсы без повторов).
    Кейс имеет повтор, если хотя бы одна операция встретилась в нём > 1 раза."""
    case_stats = df.groupby("case_id").agg(
        n_events=("activity", "count"),
        n_unique=("activity", "nunique"),
    )
    case_stats["has_rework"] = case_stats["n_events"] > case_stats["n_unique"]
    with_rework = set(case_stats[case_stats["has_rework"]].index)
    without_rework = set(case_stats[~case_stats["has_rework"]].index)
    return with_rework, without_rework


def compute_duration_comparison(df: pd.DataFrame) -> dict[str, float | int | None]:
    """Сравнение средней длительности кейсов с повторами и без."""
    case_dur = compute_case_duration(df)
    with_rework, without_rework = split_cases_by_rework(df)

    avg_with = case_dur[case_dur["case_id"].isin(with_rework)]["duration_seconds"].mean()
    avg_without = case_dur[case_dur["case_id"].isin(without_rework)][
        "duration_seconds"
    ].mean()

    return {
        "avg_duration_with_rework_seconds": (
            float(avg_with) if not pd.isna(avg_with) else None
        ),
        "avg_duration_without_rework_seconds": (
            float(avg_without) if not pd.isna(avg_without) else None
        ),
        "n_cases_with_rework": len(with_rework),
        "n_cases_without_rework": len(without_rework),
    }
