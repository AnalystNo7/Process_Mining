from datetime import datetime, timezone

import pandas as pd

from app.domain.mining.duration import (
    compute_case_duration,
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
