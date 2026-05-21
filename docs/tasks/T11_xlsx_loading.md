# T11: Парсинг xlsx и маппинг колонок

## Цель
Чистая функция `load_event_log(path, column_mapping) -> DataFrame`, преобразующая произвольный xlsx в стандартизованный формат.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/loading.py"
- `golden_data/synthetic_log.xlsx` — тестовый файл

## DoD
- [ ] Функция `load_event_log(file_path, column_mapping)` в `app/domain/mining/loading.py`.
- [ ] Функция `validate_event_log(df) -> ValidationReport`.
- [ ] Функция `deduplicate(df) -> (df, n_removed)`.
- [ ] Функция `parse_excel_datetime(series)` — корректный парсинг Excel-чисел и строк-дат.
- [ ] Поддержка обязательных полей (case_id, activity, timestamp_start, timestamp_end) и опциональных (resource, department, additional dict).
- [ ] Локализация timestamps в МСК → конвертация в UTC для возврата.
- [ ] Unit-тесты + golden test (загрузка synthetic_log.xlsx → 25606 строк после dedup).

## Реализация

### Псевдокод
```python
def load_event_log(file_path: Path, column_mapping: dict) -> pd.DataFrame:
    raw = pd.read_excel(file_path, sheet_name=0)
    
    # Маппим обязательные поля
    result = pd.DataFrame()
    for std_field in ["case_id", "activity", "timestamp_start", "timestamp_end"]:
        src = column_mapping[std_field]
        if src not in raw.columns:
            raise ValueError(f"Column {src!r} not found")
        result[std_field] = raw[src]
    
    # Типизация
    result["case_id"] = result["case_id"].astype(str)
    result["activity"] = result["activity"].astype(str)
    result["timestamp_start"] = parse_excel_datetime(result["timestamp_start"])
    result["timestamp_end"] = parse_excel_datetime(result["timestamp_end"])
    
    # Локализуем МСК → UTC
    result["timestamp_start"] = result["timestamp_start"].dt.tz_localize("Europe/Moscow", ambiguous="infer").dt.tz_convert("UTC")
    result["timestamp_end"] = result["timestamp_end"].dt.tz_localize("Europe/Moscow", ambiguous="infer").dt.tz_convert("UTC")
    
    # Опциональные поля
    for opt in ["resource", "department"]:
        src = column_mapping.get(opt)
        if src and src in raw.columns:
            result[opt] = raw[src].astype(str).where(raw[src].notna(), None)
        else:
            result[opt] = None
    
    # additional → attributes как dict в каждой строке
    additional_mapping = column_mapping.get("additional", {})
    if additional_mapping:
        attrs_rows = []
        for _, row in raw.iterrows():
            attrs = {}
            for std_name, src_col in additional_mapping.items():
                if src_col in raw.columns and pd.notna(row[src_col]):
                    attrs[std_name] = str(row[src_col])
            attrs_rows.append(attrs)
        result["attributes"] = attrs_rows
    else:
        result["attributes"] = [{}] * len(result)
    
    return result


def parse_excel_datetime(series: pd.Series) -> pd.Series:
    """Если series уже datetime — вернуть как есть. Если число — конвертировать как Excel-формат."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        # Excel serial date: дни от 1899-12-30
        return pd.to_datetime(series, origin="1899-12-30", unit="D")
    # Строки — парсим
    return pd.to_datetime(series, errors="raise")
```

## Тесты
```python
def test_load_synthetic_log():
    mapping = {"case_id": "doc_id", "activity": "Операция",
               "timestamp_start": "in_progress_datetime",
               "timestamp_end": "completed_datetime",
               "resource": "task_user", "department": "task_user_department"}
    df = load_event_log(GOLDEN_DIR / "synthetic_log.xlsx", mapping)
    assert len(df) == 25606
    assert df["case_id"].nunique() == 1328
    assert df["activity"].nunique() == 507
    assert df["timestamp_start"].dtype.name == "datetime64[ns, UTC]"

def test_required_column_missing_raises():
    with pytest.raises(ValueError, match="not found"):
        load_event_log("file.xlsx", {"case_id": "missing", ...})

def test_validate_detects_null_in_required():
    df = pd.DataFrame({"case_id": ["A", None], "activity": ["X", "Y"], ...})
    report = validate_event_log(df)
    assert len(report.errors) > 0

def test_deduplicate_removes_exact_duplicates():
    df = pd.DataFrame([same_row, same_row])
    deduped, n_removed = deduplicate(df)
    assert n_removed == 1
```

## Acceptance
`pytest tests/unit/domain/mining/test_loading.py` всё зелёное + golden test `test_load_synthetic_log` зелёный.
