from datetime import datetime

import pandas as pd
import pytest

from app.domain.mining.loading import (
    deduplicate,
    load_event_log,
    parse_excel_datetime,
    validate_event_log,
)

_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
    "resource": "user",
    "department": "dept",
}


def _write_xlsx(tmp_path, rows: list[dict]) -> str:
    path = tmp_path / "log.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    return str(path)


def test_parse_excel_datetime_numeric() -> None:
    result = parse_excel_datetime(pd.Series([45292.0]))
    assert pd.api.types.is_datetime64_any_dtype(result)
    assert result.iloc[0] == datetime(2024, 1, 1)


def test_parse_excel_datetime_already_datetime() -> None:
    series = pd.Series(pd.to_datetime(["2025-03-01", "2025-03-02"]))
    result = parse_excel_datetime(series)
    assert pd.api.types.is_datetime64_any_dtype(result)


def test_load_event_log_basic(tmp_path) -> None:
    path = _write_xlsx(
        tmp_path,
        [
            {
                "doc_id": "D1",
                "op": "Регистрация",
                "t_start": datetime(2025, 1, 9, 10, 0),
                "t_end": datetime(2025, 1, 9, 11, 0),
                "user": "Иванов",
                "dept": "Договорной отдел",
            }
        ],
    )
    df = load_event_log(path, _MAPPING)
    assert list(df.columns) == [
        "case_id", "activity", "timestamp_start", "timestamp_end",
        "resource", "department", "attributes",
    ]
    assert df["case_id"].iloc[0] == "D1"
    assert str(df["timestamp_start"].dtype).endswith("UTC]")
    # 10:00 МСК → 07:00 UTC
    assert df["timestamp_start"].iloc[0].hour == 7


def test_load_event_log_tz_aware_input(tmp_path) -> None:
    """Времена в файле — строки со смещением (+03:00), pandas читает их как
    tz-aware. Не падаем, доверяем смещению из файла и переводим в UTC:
    10:00+03:00 → 07:00 UTC (Excel не хранит tz, поэтому вход — строки)."""
    path = _write_xlsx(
        tmp_path,
        [
            {
                "doc_id": "D1",
                "op": "Регистрация",
                "t_start": "2025-01-09 10:00:00+03:00",
                "t_end": "2025-01-09 11:00:00+03:00",
                "user": "Иванов",
                "dept": "Договорной отдел",
            }
        ],
    )
    df = load_event_log(path, _MAPPING)
    assert str(df["timestamp_start"].dtype).endswith("UTC]")
    assert df["timestamp_start"].iloc[0].hour == 7


def test_load_event_log_header_row(tmp_path) -> None:
    """Файл с шапкой отчёта: заголовки на 3-й строке (header_row=2)."""
    path = tmp_path / "log.xlsx"
    grid = [
        ["Отчёт за январь", None, None, None, None, None],
        [None, None, None, None, None, None],
        ["doc_id", "op", "t_start", "t_end", "user", "dept"],
        ["D1", "Регистрация", datetime(2025, 1, 9, 10, 0),
         datetime(2025, 1, 9, 11, 0), "Иванов", "Договорной отдел"],
    ]
    pd.DataFrame(grid).to_excel(path, index=False, header=False)

    df = load_event_log(str(path), _MAPPING, header_row=2)
    assert len(df) == 1
    assert df["case_id"].iloc[0] == "D1"
    assert df["activity"].iloc[0] == "Регистрация"


def test_load_event_log_sheet_name(tmp_path) -> None:
    """Данные на втором листе — читаем именно его по имени."""
    path = tmp_path / "multi.xlsx"
    row = {
        "doc_id": "D9", "op": "Проверка",
        "t_start": datetime(2025, 2, 1, 10, 0),
        "t_end": datetime(2025, 2, 1, 11, 0),
        "user": "П", "dept": "Отдел",
    }
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([{"x": 1}]).to_excel(writer, sheet_name="Пусто", index=False)
        pd.DataFrame([row]).to_excel(writer, sheet_name="Данные", index=False)

    df = load_event_log(str(path), _MAPPING, sheet_name="Данные")
    assert len(df) == 1
    assert df["case_id"].iloc[0] == "D9"


def test_load_event_log_additional_attributes(tmp_path) -> None:
    path = _write_xlsx(
        tmp_path,
        [
            {
                "doc_id": "D1", "op": "X",
                "t_start": datetime(2025, 1, 9, 10, 0),
                "t_end": datetime(2025, 1, 9, 11, 0),
                "user": "U", "dept": "D", "doc_type": "Договор",
            }
        ],
    )
    mapping = {**_MAPPING, "additional": {"doc_type": "doc_type"}}
    df = load_event_log(path, mapping)
    assert df["attributes"].iloc[0] == {"doc_type": "Договор"}


def test_required_column_missing_raises(tmp_path) -> None:
    path = _write_xlsx(tmp_path, [{"a": 1, "b": 2}])
    with pytest.raises(ValueError, match="не найдена"):
        load_event_log(
            path,
            {"case_id": "missing", "activity": "a", "timestamp_start": "b",
             "timestamp_end": "b"},
        )


def test_validate_detects_null_in_required() -> None:
    t = datetime(2025, 1, 1)
    df = pd.DataFrame(
        {
            "case_id": ["A", None],
            "activity": ["X", "Y"],
            "timestamp_start": [t, t],
            "timestamp_end": [t, t],
        }
    )
    report = validate_event_log(df)
    assert not report.is_valid
    assert any("case_id" in e for e in report.errors)


def test_validate_detects_bad_time_order() -> None:
    df = pd.DataFrame(
        {
            "case_id": ["A"],
            "activity": ["X"],
            "timestamp_start": [datetime(2025, 1, 2)],
            "timestamp_end": [datetime(2025, 1, 1)],
        }
    )
    report = validate_event_log(df)
    assert not report.is_valid


def test_validate_ok() -> None:
    df = pd.DataFrame(
        {
            "case_id": ["A", "B"],
            "activity": ["X", "Y"],
            "timestamp_start": [datetime(2025, 1, 1), datetime(2025, 1, 1)],
            "timestamp_end": [datetime(2025, 1, 2), datetime(2025, 1, 2)],
        }
    )
    report = validate_event_log(df)
    assert report.is_valid


def test_validate_empty_dataframe() -> None:
    report = validate_event_log(pd.DataFrame())
    assert not report.is_valid


def test_deduplicate_removes_exact_duplicates() -> None:
    t = datetime(2025, 1, 1)
    row = {"case_id": "A", "activity": "X", "timestamp_start": t, "timestamp_end": t}
    df = pd.DataFrame([row, row, {**row, "case_id": "B"}])
    deduped, removed = deduplicate(df)
    assert removed == 1
    assert len(deduped) == 2
