"""Health-check датасета — оценка пригодности для анализа (см. 02_DOMAIN_LOGIC.md).

Сама функция health_check относится к задаче T13; реализована здесь раньше,
так как конвейер загрузки (T12) обязан заполнять health_report датасета."""

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

Severity = Literal["info", "warning", "error"]
HealthStatus = Literal["good", "warning", "poor"]


@dataclass
class HealthCheck:
    name: str
    severity: Severity
    message: str
    value: Any


@dataclass
class HealthReport:
    status: HealthStatus
    checks: list[HealthCheck]


def _global_rework_pct(df: pd.DataFrame) -> float:
    """Доля повторных операций. Полная реализация — в rework.py (T19)."""
    if len(df) == 0:
        return 0.0
    counts = df.groupby(["case_id", "activity"]).size()
    total = int(counts.sum())
    repeats = int((counts - 1).clip(lower=0).sum())
    return round(repeats / total * 100, 2) if total else 0.0


def health_check(df: pd.DataFrame) -> HealthReport:
    """Проверяет пригодность датасета для анализа. 5 проверок, цветовая метка."""
    checks: list[HealthCheck] = []
    n_cases = int(df["case_id"].nunique()) if len(df) else 0
    n_events = len(df)

    # 1. Минимум кейсов.
    if n_cases < 50:
        checks.append(
            HealthCheck(
                "cases_count", "error",
                f"Только {n_cases} кейсов. Статистически недостаточно для надёжного "
                "анализа (минимум 50).", n_cases,
            )
        )
    elif n_cases < 200:
        checks.append(
            HealthCheck(
                "cases_count", "warning",
                f"{n_cases} кейсов. Анализ по подразделениям/исполнителям может быть "
                "нестабильным.", n_cases,
            )
        )
    else:
        checks.append(
            HealthCheck(
                "cases_count", "info",
                f"{n_cases} кейсов — достаточно для надёжного анализа.", n_cases,
            )
        )

    # 2. Среднее число событий на кейс.
    avg_events = round(n_events / n_cases, 1) if n_cases else 0.0
    if avg_events < 3:
        checks.append(
            HealthCheck(
                "events_per_case", "warning",
                f"Среднее число операций на кейс — {avg_events}. Слишком мало для "
                "содержательного анализа последовательностей.", avg_events,
            )
        )
    else:
        checks.append(
            HealthCheck(
                "events_per_case", "info",
                f"Среднее число операций на кейс: {avg_events}", avg_events,
            )
        )

    # 3. Глобальный rework.
    rework_pct = _global_rework_pct(df)
    if rework_pct < 5:
        checks.append(
            HealthCheck(
                "rework_pct", "warning",
                f"Глобальный % повторов — {rework_pct}%. Анализ зацикленностей может "
                "не дать значимых результатов.", rework_pct,
            )
        )
    else:
        checks.append(
            HealthCheck(
                "rework_pct", "info",
                f"Глобальный % повторов: {rework_pct}%", rework_pct,
            )
        )

    # 4. Наличие поля department.
    if "department" not in df.columns or bool(df["department"].isna().all()):
        checks.append(
            HealthCheck(
                "department_field", "warning",
                "Поле подразделения не замаплено. Анализ по ролям и SLA по "
                "подразделениям недоступен.", None,
            )
        )
    else:
        checks.append(
            HealthCheck("department_field", "info", "Поле подразделения замаплено.", None)
        )

    # 5. Наличие поля resource.
    if "resource" not in df.columns or bool(df["resource"].isna().all()):
        checks.append(
            HealthCheck(
                "resource_field", "warning",
                "Поле исполнителя не замаплено. Анализ по сотрудникам недоступен.", None,
            )
        )
    else:
        checks.append(
            HealthCheck("resource_field", "info", "Поле исполнителя замаплено.", None)
        )

    has_error = any(c.severity == "error" for c in checks)
    has_warning = any(c.severity == "warning" for c in checks)
    status: HealthStatus = "poor" if has_error else "warning" if has_warning else "good"
    return HealthReport(status=status, checks=checks)
