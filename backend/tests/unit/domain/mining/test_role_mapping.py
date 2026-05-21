import pandas as pd

from app.domain.mining.role_mapping import (
    apply_role_mapping,
    get_activity_breakdown,
    suggest_role_mapping,
)

_TEMPLATES = [
    {"role_name": "Юридическое управление", "patterns": ["Юридическое управление", "ЮУ"]},
    {"role_name": "Финансовый блок", "patterns": ["Финансовое управление"]},
]


def test_suggest_matches_pattern() -> None:
    result = suggest_role_mapping(
        ["Юридическое управление", "Финансовое управление"], _TEMPLATES
    )
    assert result["Юридическое управление"][0] == "Юридическое управление"
    assert result["Финансовое управление"][0] == "Финансовый блок"
    assert result["Финансовое управление"][1] == "Финансовое управление"


def test_suggest_unknown_returns_unmapped() -> None:
    result = suggest_role_mapping(["Проект 042"], _TEMPLATES)
    assert result["Проект 042"] == ("Не размечено", None)


def test_apply_role_mapping_renames_activity() -> None:
    df = pd.DataFrame(
        {
            "case_id": ["C1"],
            "activity": ["Согласование Проект 001"],
            "department": ["Проект 001"],
        }
    )
    out = apply_role_mapping(df, {"Проект 001": "Инициатор"})
    assert out["role"].iloc[0] == "Инициатор"
    assert out["activity_with_role"].iloc[0] == "Согласование Инициатор"


def test_apply_role_mapping_keeps_when_role_equals_dept() -> None:
    df = pd.DataFrame(
        {
            "case_id": ["C1"],
            "activity": ["Согласование Юридическое управление"],
            "department": ["Юридическое управление"],
        }
    )
    out = apply_role_mapping(
        df, {"Юридическое управление": "Юридическое управление"}
    )
    assert out["activity_with_role"].iloc[0] == "Согласование Юридическое управление"


def test_apply_role_mapping_unmapped_department() -> None:
    df = pd.DataFrame(
        {"case_id": ["C1"], "activity": ["X"], "department": ["Неизвестное"]}
    )
    out = apply_role_mapping(df, {})
    assert out["role"].iloc[0] == "Не размечено"


def test_get_activity_breakdown() -> None:
    df = pd.DataFrame(
        {
            "case_id": ["C1", "C2", "C3"],
            "activity": ["Согл. Проект 1", "Согл. Проект 2", "Согл. Проект 1"],
            "activity_with_role": ["Согл. Инициатор"] * 3,
        }
    )
    breakdown = get_activity_breakdown(df, "Согл. Инициатор")
    assert set(breakdown["activity"]) == {"Согл. Проект 1", "Согл. Проект 2"}
    assert int(breakdown[breakdown["activity"] == "Согл. Проект 1"]["events"].iloc[0]) == 2
