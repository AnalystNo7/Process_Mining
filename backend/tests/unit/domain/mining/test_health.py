from datetime import datetime, timedelta

import pandas as pd

from app.domain.mining.health import health_check

_BASE = datetime(2025, 1, 1)


def _make_df(
    n_cases: int,
    events_per_case: int = 8,
    with_rework: bool = True,
    with_department: bool = True,
    with_resource: bool = True,
) -> pd.DataFrame:
    rows = []
    for case in range(n_cases):
        for ev in range(events_per_case):
            # Повтор операции "A" внутри кейса даёт rework.
            activity = "A" if (with_rework and ev % 2 == 0) else f"Act{ev}"
            rows.append(
                {
                    "case_id": f"C{case}",
                    "activity": activity,
                    "timestamp_start": _BASE + timedelta(hours=ev),
                    "timestamp_end": _BASE + timedelta(hours=ev, minutes=30),
                    "department": f"Dept{case % 3}" if with_department else None,
                    "resource": f"User{case % 5}" if with_resource else None,
                }
            )
    return pd.DataFrame(rows)


def test_health_poor_on_small_dataset() -> None:
    report = health_check(_make_df(n_cases=10))
    assert report.status == "poor"
    assert any(c.name == "cases_count" and c.severity == "error" for c in report.checks)


def test_health_warning_on_low_rework() -> None:
    report = health_check(_make_df(n_cases=250, with_rework=False))
    assert report.status == "warning"
    assert any(c.name == "rework_pct" and c.severity == "warning" for c in report.checks)


def test_health_warning_on_missing_department() -> None:
    report = health_check(_make_df(n_cases=250, with_department=False))
    assert report.status == "warning"
    assert any(
        c.name == "department_field" and c.severity == "warning" for c in report.checks
    )


def test_health_good_on_healthy_dataset() -> None:
    report = health_check(_make_df(n_cases=250))
    assert report.status == "good"
    assert all(c.severity == "info" for c in report.checks)


def test_health_report_has_five_checks() -> None:
    report = health_check(_make_df(n_cases=250))
    names = {c.name for c in report.checks}
    assert names == {
        "cases_count",
        "events_per_case",
        "rework_pct",
        "department_field",
        "resource_field",
    }
