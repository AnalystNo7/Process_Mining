"""Маппинг подразделений на роли (см. 02_DOMAIN_LOGIC.md)."""

from typing import Any

import pandas as pd

UNMAPPED_ROLE = "Не размечено"


def suggest_role_mapping(
    departments: list[str], global_templates: list[dict[str, Any]]
) -> dict[str, tuple[str, str | None]]:
    """Для каждого подразделения подбирает роль по паттернам глобальных шаблонов.

    Возвращает {подразделение: (роль, сработавший_паттерн|None)}.
    Не найденные → ('Не размечено', None)."""
    result: dict[str, tuple[str, str | None]] = {}
    for dept in departments:
        matched_role: str | None = None
        matched_pattern: str | None = None
        for template in global_templates:
            for pattern in template.get("patterns", []):
                if pattern and pattern.lower() in dept.lower():
                    matched_role = template["role_name"]
                    matched_pattern = pattern
                    break
            if matched_role is not None:
                break
        result[dept] = (matched_role or UNMAPPED_ROLE, matched_pattern)
    return result


def apply_role_mapping(df: pd.DataFrame, role_mapping: dict[str, str]) -> pd.DataFrame:
    """Добавляет колонки role (подразделение → роль) и activity_with_role
    (имя операции с заменой подразделения на роль). Исходная activity сохраняется."""
    result = df.copy()
    result["role"] = result["department"].map(role_mapping).fillna(UNMAPPED_ROLE)

    def _remap(activity: str, department: Any) -> str:
        if department is None or (isinstance(department, float) and pd.isna(department)):
            return activity
        role = role_mapping.get(department, UNMAPPED_ROLE)
        if role == department:
            return activity
        if department in activity:
            return activity.replace(department, role)
        return activity

    result["activity_with_role"] = [
        _remap(a, d) for a, d in zip(result["activity"], result["department"], strict=True)
    ]
    return result


def get_activity_breakdown(
    df_with_roles: pd.DataFrame, activity_with_role: str
) -> pd.DataFrame:
    """Для роль-операции возвращает исходные имена операций с числом событий/кейсов."""
    mask = df_with_roles["activity_with_role"] == activity_with_role
    return (
        df_with_roles[mask]
        .groupby("activity")
        .agg(events=("case_id", "count"), cases=("case_id", "nunique"))
        .reset_index()
        .sort_values("events", ascending=False)
        .reset_index(drop=True)
    )
