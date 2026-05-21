"""Расчёт SLA-комплаенса (см. 02_DOMAIN_LOGIC.md, T34).

Примечания по реализации:
- метод календаря — working_hours (в тексте T34 он назван workhours_between);
- target_pct берётся из сработавшего правила (target_compliance_pct),
  а не из захардкоженной константы;
- цикл согласования в MVP отсутствует — SLA-правило не имеет измерения
  cycle_number (см. глоссарий 00_OVERVIEW)."""

from typing import Any

import pandas as pd

from app.domain.mining.workday import WORK_HOURS_PER_DAY, WorkdayCalculator

_HOURS_PER_CALENDAR_DAY = 24.0


def find_matching_rule(
    rules: list[dict[str, Any]], operation: str, role: str
) -> dict[str, Any] | None:
    """Находит наиболее специфичное SLA-правило для (операция, роль).

    Приоритет: точные role+operation > role+'*' > '*'+operation > '*'+'*'."""
    candidates = [
        rule
        for rule in rules
        if rule["role"] in (role, "*")
        and rule["operation_pattern"] in (operation, "*")
    ]
    if not candidates:
        return None

    def specificity(rule: dict[str, Any]) -> int:
        return (2 if rule["role"] != "*" else 0) + (
            1 if rule["operation_pattern"] != "*" else 0
        )

    candidates.sort(key=specificity, reverse=True)
    return candidates[0]


def threshold_hours(rule: dict[str, Any]) -> float:
    """Норматив SLA в рабочих часах."""
    unit = rule["sla_unit"]
    value = float(rule["sla_value"])
    if unit == "workdays":
        return value * WORK_HOURS_PER_DAY
    if unit == "calendar_days":
        return value * _HOURS_PER_CALENDAR_DAY
    return value  # workhours, hours


def evaluate_sla(
    df: pd.DataFrame,
    sla_rules: list[dict[str, Any]],
    calendar: WorkdayCalculator,
) -> pd.DataFrame:
    """Для каждого события: подбирает SLA-правило, считает длительность с учётом
    перехода в рабочих часах, определяет нарушение."""
    work = df.sort_values(["case_id", "timestamp_end"]).reset_index(drop=True)
    work["prev_end"] = work.groupby("case_id")["timestamp_end"].shift(1)

    rule_ids: list[int | None] = []
    targets: list[float | None] = []
    sojourns: list[float] = []
    overdue: list[bool] = []

    for row in work.itertuples(index=False):
        sla_start = row.prev_end if pd.notna(row.prev_end) else row.timestamp_start
        sojourn = calendar.working_hours(sla_start, row.timestamp_end)
        sojourns.append(sojourn)

        role = getattr(row, "role", "*")
        rule = find_matching_rule(sla_rules, str(row.activity), str(role))
        if rule is None:
            rule_ids.append(None)
            targets.append(None)
            overdue.append(False)
            continue
        limit = threshold_hours(rule) + float(rule["tolerance_hours"])
        rule_ids.append(int(rule["id"]))
        targets.append(float(rule["target_compliance_pct"]))
        overdue.append(sojourn > limit)

    work["sla_rule_id"] = rule_ids
    work["sla_target_pct"] = targets
    work["sojourn_workhours"] = sojourns
    work["is_overdue"] = overdue
    return work


def aggregate_sla_compliance(evaluated: pd.DataFrame) -> dict[str, Any]:
    """Агрегирует результат evaluate_sla по операциям."""
    rows: list[dict[str, Any]] = []
    for activity, group in evaluated.groupby("activity"):
        total = int(len(group))
        with_sla = int(group["sla_rule_id"].notna().sum())
        overdue_count = int(group["is_overdue"].sum())
        compliance = (
            round((with_sla - overdue_count) / with_sla * 100, 2)
            if with_sla
            else None
        )
        targets = group.loc[group["sla_target_pct"].notna(), "sla_target_pct"]
        target = float(targets.iloc[0]) if len(targets) else 90.0
        role = str(group["role"].iloc[0]) if "role" in group.columns else "*"

        if compliance is None:
            status = "no_rule"
        elif compliance >= target:
            status = "good"
        elif compliance >= target - 5:
            status = "warning"
        else:
            status = "poor"

        rows.append(
            {
                "activity": str(activity),
                "role": role,
                "total_events": total,
                "events_with_sla": with_sla,
                "overdue_count": overdue_count,
                "compliance_pct": compliance,
                "target_pct": target,
                "status": status,
            }
        )

    rows.sort(key=lambda r: r["total_events"], reverse=True)
    total_with_sla = int(evaluated["sla_rule_id"].notna().sum())
    total_overdue = int(evaluated["is_overdue"].sum())
    overall = (
        round((total_with_sla - total_overdue) / total_with_sla * 100, 2)
        if total_with_sla
        else None
    )
    return {"rows": rows, "overall_compliance_pct": overall}
