"""Загрузка и валидация журнала событий из xlsx (см. 02_DOMAIN_LOGIC.md)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_FIELDS = ["case_id", "activity", "timestamp_start", "timestamp_end"]
_DEDUP_KEYS = ["case_id", "activity", "timestamp_start", "timestamp_end"]


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def parse_excel_datetime(series: pd.Series) -> pd.Series:
    """Парсит столбец дат: datetime — как есть, число — как Excel-дата
    (дни от 1899-12-30), строка — через pandas-парсер."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, origin="1899-12-30", unit="D")
    return pd.to_datetime(series, errors="raise")


def _localize_msk_to_utc(series: pd.Series) -> pd.Series:
    """Приводит времена к UTC. Если в файле уже есть смещение (tz-aware) —
    доверяем ему и просто переводим в UTC. Наивное время считаем московским
    локальным и локализуем в Europe/Moscow."""
    if series.dt.tz is not None:
        return series.dt.tz_convert("UTC")
    return series.dt.tz_localize(
        "Europe/Moscow", ambiguous="NaT", nonexistent="shift_forward"
    ).dt.tz_convert("UTC")


def load_event_log(
    file_path: Path | str, column_mapping: dict[str, Any], header_row: int = 0
) -> pd.DataFrame:
    """Загружает xlsx, применяет маппинг колонок, возвращает стандартизованный
    DataFrame с колонками case_id, activity, timestamp_start, timestamp_end,
    resource, department, attributes. header_row — номер строки заголовков
    (0-based); должен совпадать с разбором на этапе preview."""
    raw = pd.read_excel(file_path, sheet_name=0, header=header_row)

    result = pd.DataFrame()
    for std_field in REQUIRED_FIELDS:
        src = column_mapping.get(std_field)
        if src is None or src not in raw.columns:
            raise ValueError(f"Колонка {src!r} не найдена в файле")
        result[std_field] = raw[src]

    result["case_id"] = result["case_id"].astype(str)
    result["activity"] = result["activity"].astype(str)
    result["timestamp_start"] = _localize_msk_to_utc(
        parse_excel_datetime(result["timestamp_start"])
    )
    result["timestamp_end"] = _localize_msk_to_utc(
        parse_excel_datetime(result["timestamp_end"])
    )

    for opt in ["resource", "department"]:
        src = column_mapping.get(opt)
        if src and src in raw.columns:
            # Явный list comp: пропущенные значения → Python None
            # (astype(str) в pandas 3.0 может оставлять NaN как float).
            result[opt] = [
                str(value) if pd.notna(value) else None for value in raw[src]
            ]
        else:
            result[opt] = None

    additional: dict[str, str] = column_mapping.get("additional", {})
    if additional:
        attrs_rows: list[dict[str, str]] = []
        for _, row in raw.iterrows():
            attrs: dict[str, str] = {}
            for std_name, src_col in additional.items():
                if src_col in raw.columns and pd.notna(row[src_col]):
                    attrs[std_name] = str(row[src_col])
            attrs_rows.append(attrs)
        result["attributes"] = attrs_rows
    else:
        result["attributes"] = [{} for _ in range(len(result))]

    return result


def validate_event_log(df: pd.DataFrame) -> ValidationReport:
    """Проверяет загруженный журнал: пустые обязательные поля, корректность
    времён, наличие данных."""
    report = ValidationReport()
    if len(df) == 0:
        report.errors.append("Файл не содержит ни одной строки данных")
        return report

    for col in ["timestamp_start", "timestamp_end"]:
        n_null = int(df[col].isna().sum())
        if n_null > 0:
            report.errors.append(f"Колонка {col!r} содержит {n_null} пустых значений")

    for col in ["case_id", "activity"]:
        n_null = int(df[col].isna().sum())
        non_null = df[col].dropna().astype(str).str.strip()
        n_blank = int((non_null == "").sum())
        n_empty = n_null + n_blank
        if n_empty > 0:
            report.errors.append(f"Колонка {col!r} содержит {n_empty} пустых значений")

    bad_order = int((df["timestamp_end"] < df["timestamp_start"]).sum())
    if bad_order > 0:
        report.errors.append(
            f"В {bad_order} строках timestamp_end раньше timestamp_start"
        )

    n_zero = int((df["timestamp_end"] == df["timestamp_start"]).sum())
    if n_zero / len(df) > 0.8:
        report.warnings.append(
            f"{n_zero} операций ({n_zero / len(df) * 100:.1f}%) имеют нулевую "
            "длительность — это нормально для системных событий СЭД, но влияет "
            "на метрики собственной длительности."
        )

    return report


def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Удаляет точные дубликаты событий. Возвращает (очищенный df, удалено)."""
    before = len(df)
    dedup_cols = list(_DEDUP_KEYS)
    if "resource" in df.columns:
        dedup_cols.append("resource")
    deduped = df.drop_duplicates(subset=dedup_cols, keep="first").reset_index(drop=True)
    return deduped, before - len(deduped)
