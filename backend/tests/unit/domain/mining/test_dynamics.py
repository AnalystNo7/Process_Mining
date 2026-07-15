from datetime import datetime, timezone

import pandas as pd

from app.domain.mining.dynamics import compute_monthly_dynamics


def _ev(case: str, activity: str, month: int, day: int = 15, year: int = 2025) -> dict:
    return {
        "case_id": case,
        "activity": activity,
        "timestamp_start": datetime(year, month, day, 12, 0, tzinfo=timezone.utc),
        "timestamp_end": datetime(year, month, day, 13, 0, tzinfo=timezone.utc),
    }


def test_monthly_dynamics_three_months() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 1), _ev("C2", "A", 2), _ev("C3", "A", 3)]
    )
    result = compute_monthly_dynamics(df)
    assert len(result) == 3
    assert list(result["month"]) == ["2025-01", "2025-02", "2025-03"]


def test_dynamics_granularity_day() -> None:
    # Три события в одном месяце, но в разные дни → 3 суточных бакета.
    df = pd.DataFrame(
        [_ev("C1", "A", 1, day=1), _ev("C2", "A", 1, day=2), _ev("C3", "A", 1, day=3)]
    )
    result = compute_monthly_dynamics(df, granularity="D")
    assert list(result["month"]) == ["2025-01-01", "2025-01-02", "2025-01-03"]


def test_dynamics_granularity_quarter() -> None:
    # Январь и апрель → разные кварталы.
    df = pd.DataFrame([_ev("C1", "A", 1), _ev("C2", "A", 4)])
    result = compute_monthly_dynamics(df, granularity="Q")
    assert list(result["month"]) == ["2025Q1", "2025Q2"]


def test_dynamics_granularity_year() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 6, year=2024), _ev("C2", "A", 6, year=2025)]
    )
    result = compute_monthly_dynamics(df, granularity="Y")
    assert list(result["month"]) == ["2024", "2025"]


def test_monthly_dynamics_activity_filter() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 1), _ev("C2", "B", 1), _ev("C3", "A", 2)]
    )
    result = compute_monthly_dynamics(df, activity_filter="A")
    assert int(result["n_events"].sum()) == 2


def test_monthly_dynamics_empty() -> None:
    df = pd.DataFrame(
        columns=["case_id", "activity", "timestamp_start", "timestamp_end"]
    )
    assert len(compute_monthly_dynamics(df)) == 0
