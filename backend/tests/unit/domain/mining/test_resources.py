from datetime import datetime, timedelta, timezone

import pandas as pd

from app.domain.mining.resources import compute_resource_workload

_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ev(case: str, activity: str, resource: str, hour: int) -> dict:
    return {
        "case_id": case,
        "activity": activity,
        "resource": resource,
        "timestamp_start": _BASE + timedelta(hours=hour),
        "timestamp_end": _BASE + timedelta(hours=hour + 1),
    }


def test_resource_workload() -> None:
    df = pd.DataFrame(
        [
            _ev("C1", "A", "Иванов", 0),
            _ev("C1", "B", "Иванов", 1),
            _ev("C2", "A", "Петров", 2),
        ]
    )
    result = compute_resource_workload(df)
    ivanov = result[result["resource"] == "Иванов"].iloc[0]
    assert ivanov["n_events"] == 2
    assert ivanov["n_cases"] == 1
    assert ivanov["n_unique_activities"] == 2
    # Иванов с 2 событиями — первый в сортировке по n_events.
    assert result.iloc[0]["resource"] == "Иванов"


def test_resource_workload_sorted_by_events() -> None:
    df = pd.DataFrame(
        [
            _ev("C1", "A", "Мало", 0),
            _ev("C2", "A", "Много", 1),
            _ev("C3", "B", "Много", 2),
        ]
    )
    result = compute_resource_workload(df)
    assert list(result["resource"]) == ["Много", "Мало"]


def test_resource_workload_empty() -> None:
    df = pd.DataFrame(
        columns=["case_id", "activity", "resource", "timestamp_start", "timestamp_end"]
    )
    assert len(compute_resource_workload(df)) == 0
