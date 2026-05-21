from datetime import datetime, timezone

import pandas as pd

from app.domain.mining.sla import (
    aggregate_sla_compliance,
    evaluate_sla,
    find_matching_rule,
    threshold_hours,
)
from app.domain.mining.workday import WorkdayCalculator


def _rule(
    rule_id: int,
    role: str = "*",
    operation: str = "*",
    value: float = 3,
    unit: str = "workdays",
    tolerance: float = 0,
    target: float = 90.0,
) -> dict:
    return {
        "id": rule_id,
        "role": role,
        "operation_pattern": operation,
        "sla_value": value,
        "sla_unit": unit,
        "tolerance_hours": tolerance,
        "target_compliance_pct": target,
    }


def test_find_matching_rule_specificity() -> None:
    rules = [
        _rule(1),
        _rule(2, role="ЮУ"),
        _rule(3, role="ЮУ", operation="Согласование"),
    ]
    assert find_matching_rule(rules, "Согласование", "ЮУ")["id"] == 3
    assert find_matching_rule(rules, "Прочее", "ЮУ")["id"] == 2
    assert find_matching_rule(rules, "Прочее", "Финансы")["id"] == 1


def test_find_matching_rule_none() -> None:
    rules = [_rule(1, role="ЮУ", operation="Согласование")]
    assert find_matching_rule(rules, "Иное", "Финансы") is None


def test_threshold_hours() -> None:
    assert threshold_hours(_rule(1, value=3, unit="workdays")) == 24.0
    assert threshold_hours(_rule(1, value=2, unit="calendar_days")) == 48.0
    assert threshold_hours(_rule(1, value=5, unit="workhours")) == 5.0
    assert threshold_hours(_rule(1, value=10, unit="hours")) == 10.0


def test_evaluate_sla_marks_overdue() -> None:
    # Понедельник 13.01.2025: операция 09:00–13:00 = 4 рабочих часа.
    base = datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc)
    df = pd.DataFrame(
        [
            {
                "case_id": "C1",
                "activity": "Согласование",
                "role": "ЮУ",
                "timestamp_start": base,
                "timestamp_end": base.replace(hour=13),
            }
        ]
    )
    rules = [_rule(1, role="ЮУ", value=1, unit="workhours", tolerance=0)]
    result = evaluate_sla(df, rules, WorkdayCalculator())
    assert bool(result["is_overdue"].iloc[0]) is True
    assert result["sla_rule_id"].iloc[0] == 1


def test_evaluate_sla_no_rule() -> None:
    base = datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc)
    df = pd.DataFrame(
        [
            {
                "case_id": "C1",
                "activity": "X",
                "role": "ЮУ",
                "timestamp_start": base,
                "timestamp_end": base.replace(hour=10),
            }
        ]
    )
    result = evaluate_sla(df, [], WorkdayCalculator())
    assert result["sla_rule_id"].iloc[0] is None
    assert bool(result["is_overdue"].iloc[0]) is False


def test_aggregate_sla_compliance() -> None:
    base = datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc)
    df = pd.DataFrame(
        [
            {"case_id": "C1", "activity": "A", "role": "ЮУ",
             "timestamp_start": base, "timestamp_end": base.replace(hour=13)},
            {"case_id": "C2", "activity": "A", "role": "ЮУ",
             "timestamp_start": base, "timestamp_end": base.replace(hour=10)},
        ]
    )
    rules = [_rule(1, role="ЮУ", value=2, unit="workhours", tolerance=0, target=90.0)]
    aggregated = aggregate_sla_compliance(evaluate_sla(df, rules, WorkdayCalculator()))
    row = aggregated["rows"][0]
    assert row["activity"] == "A"
    assert row["total_events"] == 2
    assert row["events_with_sla"] == 2
    assert row["overdue_count"] == 1  # 4ч > 2ч просрочка, 1ч — нет
    assert row["compliance_pct"] == 50.0
