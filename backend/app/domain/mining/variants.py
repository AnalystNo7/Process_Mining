"""Варианты процесса и анализ путей (см. 02_DOMAIN_LOGIC.md)."""

from typing import Any

import pandas as pd

from app.domain.mining.duration import compute_case_duration


def get_case_traces(df: pd.DataFrame, activity_col: str = "activity") -> pd.Series:
    """Для каждого кейса — кортеж операций в хронологическом порядке.
    Возвращает Series: index=case_id, value=tuple[str, ...]."""
    return (
        df.sort_values(["case_id", "timestamp_start", "timestamp_end"])
        .groupby("case_id")[activity_col]
        .apply(tuple)
    )


def get_top_n_variants(
    df: pd.DataFrame, n: int = 5, activity_col: str = "activity"
) -> pd.DataFrame:
    """Топ-N уникальных трасс: trace | n_cases | avg_duration_seconds |
    example_case_ids. Сортировка по n_cases убыв."""
    columns = ["trace", "n_cases", "avg_duration_seconds", "example_case_ids"]
    traces = get_case_traces(df, activity_col)
    if traces.empty:
        return pd.DataFrame(columns=columns)

    case_dur = compute_case_duration(df).set_index("case_id")
    variants: list[dict[str, Any]] = []
    for trace, case_ids in traces.groupby(traces).groups.items():
        cases_list = list(case_ids)
        avg_dur = case_dur.loc[cases_list, "duration_seconds"].mean()
        variants.append(
            {
                "trace": trace,
                "n_cases": len(cases_list),
                "avg_duration_seconds": float(avg_dur),
                "example_case_ids": [str(c) for c in cases_list[:5]],
            }
        )
    variants_df = pd.DataFrame(variants).sort_values("n_cases", ascending=False)
    return variants_df.head(n).reset_index(drop=True)


def get_variants_coverage(
    df: pd.DataFrame, n: int = 5, activity_col: str = "activity"
) -> dict[str, Any]:
    """Сколько кейсов покрывают топ-N путей."""
    traces = get_case_traces(df, activity_col)
    total_cases = int(len(traces))
    total_variants = int(traces.nunique())
    top_n = get_top_n_variants(df, n=n, activity_col=activity_col)
    covered = int(top_n["n_cases"].sum()) if len(top_n) else 0
    return {
        "total_cases": total_cases,
        "total_variants": total_variants,
        "top_n": n,
        "covered_cases": covered,
        "coverage_pct": round(covered / total_cases * 100, 2) if total_cases else 0.0,
    }


def compute_variability_pct(df: pd.DataFrame, activity_col: str = "activity") -> float:
    """Вариативность путей = уникальные трассы / число кейсов * 100.
    Чем ниже, тем стандартизованнее процесс."""
    traces = get_case_traces(df, activity_col)
    if len(traces) == 0:
        return 0.0
    return round(float(traces.nunique()) / len(traces) * 100, 2)


def compute_mean_occurrence_pct(df: pd.DataFrame, activity_col: str = "activity") -> float:
    """Средний процент кейсов, в которых встречается операция."""
    total_cases = df["case_id"].nunique()
    if total_cases == 0:
        return 0.0
    op_freq = df.groupby(activity_col)["case_id"].nunique() / total_cases * 100
    return round(float(op_freq.mean()), 2) if len(op_freq) > 0 else 0.0
