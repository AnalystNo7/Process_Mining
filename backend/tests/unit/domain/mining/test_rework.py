from datetime import datetime, timedelta, timezone

import pandas as pd

from app.domain.mining import rework

_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ev(case: str, activity: str, hour: int, dur_h: int = 1) -> dict:
    return {
        "case_id": case,
        "activity": activity,
        "timestamp_start": _BASE + timedelta(hours=hour),
        "timestamp_end": _BASE + timedelta(hours=hour + dur_h),
    }


def test_no_repeats() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C1", "B", 1), _ev("C2", "A", 2)])
    result = rework.compute_rework_per_operation(df)
    assert (result["repeats"] == 0).all()
    assert (result["rework_pct"] == 0).all()


def test_one_repeat() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C1", "A", 1), _ev("C1", "B", 2)])
    result = rework.compute_rework_per_operation(df)
    row_a = result[result["activity"] == "A"].iloc[0]
    assert row_a["total"] == 2
    assert row_a["repeats"] == 1
    assert row_a["rework_pct"] == 50.0


def test_empty_dataframe() -> None:
    df = pd.DataFrame(
        columns=["case_id", "activity", "timestamp_start", "timestamp_end"]
    )
    assert len(rework.compute_rework_per_operation(df)) == 0


def test_repeats_only_within_case() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 0), _ev("C1", "A", 1), _ev("C2", "A", 2), _ev("C2", "A", 3)]
    )
    row_a = rework.compute_rework_per_operation(df).iloc[0]
    assert row_a["total"] == 4
    assert row_a["repeats"] == 2  # по одному повтору в каждом кейсе


def test_global_rework_pct() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C1", "A", 1)])
    assert rework.compute_global_rework_pct(df) == 50.0


def test_split_cases_by_rework() -> None:
    df = pd.DataFrame(
        [
            _ev("C1", "A", 0), _ev("C1", "A", 1),  # с повтором
            _ev("C2", "A", 2), _ev("C2", "B", 3),  # без повтора
        ]
    )
    with_rework, without_rework = rework.split_cases_by_rework(df)
    assert with_rework == {"C1"}
    assert without_rework == {"C2"}


def test_operation_summary_counts() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 0), _ev("C1", "A", 2), _ev("C1", "B", 4), _ev("C2", "A", 6)]
    )
    summary = rework.compute_operation_summary(df)
    row_a = summary[summary["activity"] == "A"].iloc[0]
    assert row_a["n_cases"] == 2  # C1, C2
    assert row_a["n_events"] == 3  # три вхождения A


def test_operation_summary_durations() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0, dur_h=2), _ev("C2", "A", 6, dur_h=4)])
    row = rework.compute_operation_summary(df).iloc[0]
    assert row["avg_own_duration_seconds"] == 3 * 3600
    assert row["median_own_duration_seconds"] == 3 * 3600


def test_operation_summary_share() -> None:
    # C1: A длится 2ч, B длится 1ч; кейс тянется с 0ч до 5ч → доля A = 40%.
    df = pd.DataFrame([_ev("C1", "A", 0, dur_h=2), _ev("C1", "B", 4, dur_h=1)])
    row_a = rework.compute_operation_summary(df)
    row_a = row_a[row_a["activity"] == "A"].iloc[0]
    assert row_a["avg_share_pct"] == 40.0


def test_operation_summary_zero_duration_case() -> None:
    df = pd.DataFrame(
        [{"case_id": "C1", "activity": "A", "timestamp_start": _BASE,
          "timestamp_end": _BASE}]
    )
    row = rework.compute_operation_summary(df).iloc[0]
    assert row["n_cases"] == 1
    assert row["avg_share_pct"] == 0.0


def test_operation_summary_empty() -> None:
    df = pd.DataFrame(
        columns=["case_id", "activity", "timestamp_start", "timestamp_end"]
    )
    assert len(rework.compute_operation_summary(df)) == 0


def test_duration_comparison() -> None:
    df = pd.DataFrame(
        [
            # C1 с повтором, длится 10ч
            {"case_id": "C1", "activity": "A", "timestamp_start": _BASE,
             "timestamp_end": _BASE + timedelta(hours=10)},
            {"case_id": "C1", "activity": "A", "timestamp_start": _BASE,
             "timestamp_end": _BASE + timedelta(hours=5)},
            # C2 без повтора, длится 2ч
            {"case_id": "C2", "activity": "A", "timestamp_start": _BASE,
             "timestamp_end": _BASE + timedelta(hours=2)},
        ]
    )
    comparison = rework.compute_duration_comparison(df)
    assert comparison["n_cases_with_rework"] == 1
    assert comparison["n_cases_without_rework"] == 1
    assert comparison["avg_duration_with_rework_seconds"] == 10 * 3600
    assert comparison["avg_duration_without_rework_seconds"] == 2 * 3600
