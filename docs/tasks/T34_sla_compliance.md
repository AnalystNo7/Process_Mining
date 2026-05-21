# T34: Расчёт SLA-комплаенса

## Цель
Алгоритм определения нарушений SLA для каждого события в виртуальном датасете. Расчёт в рабочих часах с использованием производственного календаря.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "SLA-комплаенс" — главный.
- `06_TESTING.md` раздел SLA tests — должен воспроизводить цифры из PDF Газпрома.
- T17 — WorkdayCalculator.
- T33 — SLA Rules CRUD.

## DoD
- [ ] Модуль `app/domain/mining/sla.py`.
- [ ] Функция `evaluate_sla(df, sla_rules, calendar) -> pd.DataFrame` — для каждого события возвращает SLA-результат.
- [ ] Функция `aggregate_compliance(df_evaluated) -> ComplianceReport` — агрегат по операциям.
- [ ] Endpoint `GET /api/virtual-datasets/{id}/analytics/sla-compliance` — возвращает агрегированный отчёт.
- [ ] Golden tests против цифр PDF Газпрома (раздел 3 PDF — БЭФ, УКЗ, ЮУ).

## Алгоритм
```python
@dataclass
class SlaEvaluation:
    event_id: int
    case_id: str
    activity: str
    role: str
    sla_rule_id: int | None
    sla_threshold_hours: float        # норматив в рабочих часах
    actual_duration_hours: float      # фактическая sojourn в рабочих часах
    tolerance_hours: int
    is_overdue: bool                  # actual > threshold + tolerance
    overdue_by_hours: float           # actual - (threshold + tolerance), если > 0

def evaluate_sla(df: pd.DataFrame, sla_rules: list[SlaRule], 
                 calendar: WorkdayCalculator) -> pd.DataFrame:
    """Для каждого события: подобрать правило, посчитать длительность в раб.часах, 
    определить нарушение."""
    df = df.copy()
    df = df.sort_values(["case_id", "timestamp_end"])
    
    # Sojourn в рабочих часах
    df["prev_end"] = df.groupby("case_id")["timestamp_end"].shift(1)
    df["_start"] = df["prev_end"].fillna(df["timestamp_start"])
    df["sojourn_workhours"] = df.apply(
        lambda r: calendar.workhours_between(r["_start"], r["timestamp_end"]),
        axis=1
    )
    
    # Подбор правила для каждой строки
    def get_threshold_and_tolerance(row):
        rule = find_matching_rule(sla_rules, row["activity"], row.get("role", "*"), row["timestamp_end"].date())
        if rule is None:
            return None, None, None
        # Конвертация sla_value в часы (workhours)
        if rule.sla_unit == "workdays":
            threshold_h = rule.sla_value * 8.0  # 1 раб.день = 8 раб.часов
        elif rule.sla_unit == "calendar_days":
            threshold_h = rule.sla_value * 24.0  # внимание: не raw_hours
        elif rule.sla_unit == "workhours":
            threshold_h = float(rule.sla_value)
        elif rule.sla_unit == "hours":
            threshold_h = float(rule.sla_value)
        else:
            raise ValueError(rule.sla_unit)
        return rule.id, threshold_h, rule.tolerance_hours
    
    df[["sla_rule_id", "threshold_hours", "tolerance_hours"]] = df.apply(
        lambda r: pd.Series(get_threshold_and_tolerance(r)), axis=1
    )
    
    # is_overdue: только для строк где есть правило
    df["is_overdue"] = (
        df["threshold_hours"].notna() &
        (df["sojourn_workhours"] > df["threshold_hours"] + df["tolerance_hours"].fillna(0))
    )
    df["overdue_by_hours"] = (df["sojourn_workhours"] - df["threshold_hours"] - df["tolerance_hours"].fillna(0)).clip(lower=0)
    
    return df

@dataclass
class ComplianceRow:
    activity: str
    role: str
    sla_rule_id: int | None
    total_events: int
    events_with_sla: int     # для которых нашлось правило
    overdue_count: int
    compliance_pct: float    # (events_with_sla - overdue_count) / events_with_sla * 100
    target_pct: float        # из правила
    status: Literal["good", "warning", "poor"]  # = good если compliance_pct >= target_pct

@dataclass
class ComplianceReport:
    rows: list[ComplianceRow]
    overall_compliance_pct: float

def aggregate_compliance(df_evaluated: pd.DataFrame) -> ComplianceReport:
    rows = []
    for activity, group in df_evaluated.groupby("activity"):
        total = len(group)
        with_sla = group["sla_rule_id"].notna().sum()
        overdue = int(group["is_overdue"].sum())
        compliance = (with_sla - overdue) / with_sla * 100 if with_sla else None
        # target from any rule used (если разные — берём минимальный)
        targets = group[group["sla_rule_id"].notna()]["threshold_hours"].unique()  # тут условно
        # Упрощённо: target_pct берём из первого правила группы (TODO: уточнить)
        target_pct = 90.0
        status = "good" if compliance and compliance >= target_pct else "poor"
        rows.append(ComplianceRow(
            activity=activity, role=group["role"].iloc[0] if "role" in group else "*",
            sla_rule_id=group["sla_rule_id"].iloc[0] if with_sla else None,
            total_events=total, events_with_sla=int(with_sla),
            overdue_count=overdue, compliance_pct=compliance,
            target_pct=target_pct, status=status,
        ))
    
    overall_overdue = int(df_evaluated["is_overdue"].sum())
    overall_with_sla = int(df_evaluated["sla_rule_id"].notna().sum())
    overall_compliance = (overall_with_sla - overall_overdue) / overall_with_sla * 100 if overall_with_sla else 0.0
    return ComplianceReport(rows=rows, overall_compliance_pct=overall_compliance)
```

## Golden tests (эталон из PDF Газпрома)
На `synthetic_log.xlsx` + 11 SLA-правил (по 1 на каждую операцию из PDF) + production calendar Russia. Все правила: 3 workdays, tolerance 4 workhours, target 90%.

Ожидаемые цифры из PDF (раздел 3):
- Согласование Юр.управление: ~176 просрочек из 1337 (13.2%)
- Согласование ЭБ: ~167 из 1060 (15.8%)
- Согласование Финансовое управление: ~84 из 569 (14.8%)
- Согласование Управление закупок: ~91 из 793 (11.5%)
- Согласование УБУиН: ~36 из 1145 (3.1%)
- Согласование ОФП: ~4 из 346 (1.2%)
- Доп.согл. ОЭБ: ~39 из 1019 (3.8%)
- Доп.согл. УЗ: ~6 из 101 (5.9%)
- Согл. ПЭУ: ~22 из 721 (3.1%)
- Доп.согл. УБУиН: 0 из 125 (0%)
- Доп.согл. ОФП: ~3 из 1450 (0.2%)
- Доп.согл. ЮУ: ~3 из 625 (0.5%)
- Доп.согл. ОЭБ: ~39 из 1019 (3.8%)
- Проверка Договорной отдел: ~3 из 1717 (0.2%)

Tolerance ±2 нарушения (т.к. workdays calculator может слегка иначе считать пограничные случаи).

## Тесты
- `test_evaluate_sla_marks_overdue_correctly`.
- `test_sla_workdays_unit_conversion` — 3 workdays = 24 workhours.
- `test_golden_sla_compliance_yur_upravlenie` → ~176 ± 5 нарушений.
- `test_golden_sla_compliance_eb` → ~167 ± 5 нарушений.
- `test_no_sla_rule_marks_as_unknown` — события без подходящего правила имеют sla_rule_id = None и is_overdue = False (не считаем нарушением).

## Acceptance
На synthetic_log.xlsx с 11 правилами SLA общий процент комплаенса ≈ 91-92% (близко к среднему по PDF). 11 операций с правилами имеют статус близкий к цифрам Газпрома (tolerance ±10% на абсолютном числе нарушений).
