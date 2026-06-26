from datetime import datetime, timezone

import pandas as pd

from app.domain.mining.duration import (
    compute_case_duration,
    compute_operation_durations_boxplot,
    compute_own_duration,
    compute_sojourn_time,
)


def _ts(day: int, hour: int) -> datetime:
    return datetime(2025, 1, day, hour, 0, tzinfo=timezone.utc)


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_own_duration() -> None:
    df = _df(
        [{"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
          "timestamp_end": _ts(1, 12)}]
    )
    assert compute_own_duration(df).iloc[0] == 2 * 3600


def test_sojourn_first_event_equals_own_duration() -> None:
    df = _df(
        [{"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
          "timestamp_end": _ts(1, 12)}]
    )
    result = compute_sojourn_time(df)
    assert result["sojourn_seconds"].iloc[0] == 2 * 3600


def test_sojourn_subsequent_event_from_prev_end() -> None:
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 12)},
            {"case_id": "C1", "activity": "B", "timestamp_start": _ts(1, 13),
             "timestamp_end": _ts(1, 15)},
        ]
    )
    result = compute_sojourn_time(df)
    # Второе событие: 15:00 - 12:00 (конец предыдущего) = 3ч.
    second = result[result["activity"] == "B"].iloc[0]
    assert second["sojourn_seconds"] == 3 * 3600


def test_sojourn_independent_per_case() -> None:
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 11)},
            {"case_id": "C2", "activity": "A", "timestamp_start": _ts(1, 14),
             "timestamp_end": _ts(1, 16)},
        ]
    )
    result = compute_sojourn_time(df)
    # Оба — первые в своих кейсах → собственная длительность.
    assert set(result["sojourn_seconds"]) == {3600, 7200}


def test_case_duration() -> None:
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 12)},
            {"case_id": "C1", "activity": "B", "timestamp_start": _ts(2, 10),
             "timestamp_end": _ts(2, 14)},
        ]
    )
    result = compute_case_duration(df)
    row = result.iloc[0]
    assert row["n_events"] == 2
    # с 1 янв 10:00 по 2 янв 14:00 = 28ч.
    assert row["duration_seconds"] == 28 * 3600


# T45: «ящик с усами» — распределение длительности по операциям.


def test_boxplot_empty_df_returns_empty_traces() -> None:
    assert compute_operation_durations_boxplot(pd.DataFrame()) == {"traces": []}


def test_boxplot_missing_duration_column_returns_empty_traces() -> None:
    df = _df([{"activity": "A"}])
    assert compute_operation_durations_boxplot(df) == {"traces": []}


def test_boxplot_groups_by_activity_and_computes_quartiles() -> None:
    df = _df(
        [{"activity": "A", "own_duration_sec": v} for v in [10, 20, 30, 40, 50]]
        + [{"activity": "B", "own_duration_sec": v} for v in [1, 2, 3]]
    )
    result = compute_operation_durations_boxplot(df)
    by_name = {t["name"]: t for t in result["traces"]}
    assert set(by_name) == {"A", "B"}
    # A: n=5, median=30, mean=30, min=10, max=50, q1=20, q3=40 (linear).
    a = by_name["A"]
    assert a["n"] == 5
    assert a["median"] == 30.0
    assert a["mean"] == 30.0
    assert a["min"] == 10.0
    assert a["max"] == 50.0
    assert a["q1"] == 20.0
    assert a["q3"] == 40.0
    assert a["y"] == [10.0, 20.0, 30.0, 40.0, 50.0]


def test_boxplot_sorts_by_count_descending_and_applies_limit() -> None:
    # A — 5 событий, B — 3, C — 1. limit=2 → останутся A и B, без C.
    df = _df(
        [{"activity": "A", "own_duration_sec": v} for v in range(5)]
        + [{"activity": "B", "own_duration_sec": v} for v in range(3)]
        + [{"activity": "C", "own_duration_sec": 42}]
    )
    result = compute_operation_durations_boxplot(df, limit=2)
    names = [t["name"] for t in result["traces"]]
    assert names == ["A", "B"]


def test_boxplot_single_event_does_not_crash() -> None:
    df = _df([{"activity": "A", "own_duration_sec": 123.0}])
    [trace] = compute_operation_durations_boxplot(df)["traces"]
    assert trace["n"] == 1
    assert trace["median"] == 123.0
    assert trace["q1"] == trace["q3"] == 123.0


def test_boxplot_drops_null_durations() -> None:
    df = pd.DataFrame(
        {"activity": ["A", "A", "A"], "own_duration_sec": [10.0, None, 30.0]}
    )
    [trace] = compute_operation_durations_boxplot(df)["traces"]
    assert trace["n"] == 2
    assert trace["y"] == [10.0, 30.0]
