from datetime import datetime, timedelta, timezone

import pandas as pd

from app.domain.mining.filters import apply_filter, parse_filters
from app.domain.types import EventFilter

_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ev(
    case: str,
    activity: str,
    day: int,
    dept: str = "D1",
    resource: str = "U1",
    attributes: dict | None = None,
    duration_h: int = 1,
) -> dict:
    start = _BASE + timedelta(days=day)
    return {
        "case_id": case,
        "activity": activity,
        "timestamp_start": start,
        "timestamp_end": start + timedelta(hours=duration_h),
        "department": dept,
        "resource": resource,
        "attributes": attributes or {},
    }


def test_filter_empty_returns_all() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C2", "B", 1)])
    assert len(apply_filter(df, EventFilter())) == 2


def test_filter_date_range() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C2", "A", 10), _ev("C3", "A", 20)])
    result = apply_filter(
        df,
        EventFilter(date_range=(_BASE + timedelta(days=5), _BASE + timedelta(days=15))),
    )
    assert set(result["case_id"]) == {"C2"}


def test_filter_departments() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 0, dept="ЮУ"), _ev("C2", "A", 0, dept="Финансы")]
    )
    result = apply_filter(df, EventFilter(departments=["ЮУ"]))
    assert set(result["case_id"]) == {"C1"}


def test_filter_activities() -> None:
    df = pd.DataFrame([_ev("C1", "Согласование", 0), _ev("C2", "Подписание", 0)])
    result = apply_filter(df, EventFilter(activities=["Согласование"]))
    assert set(result["case_id"]) == {"C1"}


def test_filter_with_rework_true_keeps_full_traces() -> None:
    df = pd.DataFrame(
        [
            _ev("C1", "A", 0), _ev("C1", "A", 1),  # повтор
            _ev("C2", "A", 0), _ev("C2", "B", 1),  # без повтора
        ]
    )
    result = apply_filter(df, EventFilter(with_rework=True))
    assert set(result["case_id"]) == {"C1"}
    assert len(result) == 2  # вся трасса кейса сохранена


def test_filter_with_rework_false() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 0), _ev("C1", "A", 1), _ev("C2", "A", 0), _ev("C2", "B", 1)]
    )
    result = apply_filter(df, EventFilter(with_rework=False))
    assert set(result["case_id"]) == {"C2"}


def test_filter_case_duration_range() -> None:
    df = pd.DataFrame(
        [
            _ev("Short", "A", 0, duration_h=1),
            _ev("Long", "A", 0, duration_h=240),  # 10 дней
        ]
    )
    # Кейсы длительностью >= 5 дней.
    result = apply_filter(
        df, EventFilter(case_duration_range=(5 * 86400, 10**9))
    )
    assert set(result["case_id"]) == {"Long"}


def test_filter_attributes() -> None:
    df = pd.DataFrame(
        [
            _ev("C1", "A", 0, attributes={"doc_type": "Договор"}),
            _ev("C2", "A", 0, attributes={"doc_type": "Письмо"}),
        ]
    )
    result = apply_filter(df, EventFilter(attributes_filter={"doc_type": ["Договор"]}))
    assert set(result["case_id"]) == {"C1"}


def test_filter_combined() -> None:
    df = pd.DataFrame(
        [
            _ev("C1", "A", 0, dept="ЮУ"), _ev("C1", "A", 1, dept="ЮУ"),
            _ev("C2", "A", 0, dept="ЮУ"),
            _ev("C3", "A", 0, dept="Финансы"), _ev("C3", "A", 1, dept="Финансы"),
        ]
    )
    result = apply_filter(df, EventFilter(departments=["ЮУ"], with_rework=True))
    assert set(result["case_id"]) == {"C1"}


def test_parse_filters_empty() -> None:
    assert parse_filters(None) == EventFilter()
    assert parse_filters({}) == EventFilter()


def test_parse_filters_date_range() -> None:
    event_filter = parse_filters(
        {"date_range": {"from": "2025-01-01T00:00:00", "to": "2025-02-01T00:00:00"}}
    )
    assert event_filter.date_range is not None
    assert event_filter.date_range[0] == datetime(2025, 1, 1)


def test_parse_filters_case_duration() -> None:
    event_filter = parse_filters({"case_duration": {"min_days": 30}})
    assert event_filter.case_duration_range is not None
    assert event_filter.case_duration_range[0] == 30 * 86400


def test_parse_filters_passthrough_fields() -> None:
    event_filter = parse_filters(
        {"departments": ["ЮУ"], "with_rework": True, "roles": ["Инициатор"]}
    )
    assert event_filter.departments == ["ЮУ"]
    assert event_filter.with_rework is True
    assert event_filter.roles == ["Инициатор"]
