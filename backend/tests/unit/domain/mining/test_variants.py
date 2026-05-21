from datetime import datetime, timedelta, timezone

import pandas as pd

from app.domain.mining import variants

_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ev(case: str, activity: str, hour: int) -> dict:
    return {
        "case_id": case,
        "activity": activity,
        "timestamp_start": _BASE + timedelta(hours=hour),
        "timestamp_end": _BASE + timedelta(hours=hour + 1),
    }


def _case(case: str, activities: list[str]) -> list[dict]:
    return [_ev(case, act, i) for i, act in enumerate(activities)]


def test_case_traces_order() -> None:
    df = pd.DataFrame(_case("C1", ["A", "B", "C"]))
    traces = variants.get_case_traces(df)
    assert traces["C1"] == ("A", "B", "C")


def test_variability_all_unique() -> None:
    df = pd.DataFrame(
        _case("C1", ["A", "B"]) + _case("C2", ["B", "A"]) + _case("C3", ["A", "C"])
    )
    assert variants.compute_variability_pct(df) == 100.0


def test_variability_all_same() -> None:
    df = pd.DataFrame(
        sum((_case(f"C{i}", ["A", "B", "C"]) for i in range(5)), [])
    )
    assert variants.compute_variability_pct(df) == 20.0


def test_top_n_variants() -> None:
    df = pd.DataFrame(
        _case("C1", ["A", "B"])
        + _case("C2", ["A", "B"])
        + _case("C3", ["A", "C"])
    )
    top = variants.get_top_n_variants(df, n=5)
    assert int(top.iloc[0]["n_cases"]) == 2
    assert top.iloc[0]["trace"] == ("A", "B")


def test_variants_coverage() -> None:
    df = pd.DataFrame(
        _case("C1", ["A", "B"])
        + _case("C2", ["A", "B"])
        + _case("C3", ["A", "C"])
    )
    coverage = variants.get_variants_coverage(df, n=1)
    assert coverage["total_cases"] == 3
    assert coverage["total_variants"] == 2
    assert coverage["covered_cases"] == 2


def test_mean_occurrence() -> None:
    # A в 2/2 кейсов (100%), B в 1/2 (50%) → среднее 75%.
    df = pd.DataFrame(_case("C1", ["A", "B"]) + _case("C2", ["A"]))
    assert variants.compute_mean_occurrence_pct(df) == 75.0
