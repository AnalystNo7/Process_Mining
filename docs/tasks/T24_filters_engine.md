# T24: Движок фильтров и срезов

## Цель
Универсальный механизм применения фильтров к event log.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/filters.py"
- `01_DATA_MODEL.md` структура filters в named_slices, dashboards

## DoD
- [ ] Pydantic-схема `EventFilter` со всеми поддерживаемыми типами.
- [ ] Функция `apply_filter(df, filter)` в `app/domain/mining/filters.py`.
- [ ] Поддержка всех типов:
  - date_range
  - departments / roles / resources / activities (список или паттерны)
  - case_duration_range
  - with_rework: bool
  - attributes_filter (по атрибутам из jsonb)
  - case_ids
- [ ] Фильтры применяются к загруженному DataFrame (после load_to_dataframe).
- [ ] Фильтры на уровне кейса не разрывают трассу (если кейс попадает — все его события).
- [ ] Unit-тесты на каждый тип фильтра + комбинации.

## Реализация — псевдокод в `02_DOMAIN_LOGIC.md`.

## Тесты
- `test_filter_date_range`.
- `test_filter_with_rework_true_keeps_full_traces`.
- `test_filter_combined`.

## Acceptance
Применение filter с date_range + with_rework=true возвращает корректное подмножество.
