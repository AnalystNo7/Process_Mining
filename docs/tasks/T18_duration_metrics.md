# T18: Метрики длительности (sojourn, own, case)

## Цель
Чистые функции расчёта длительностей с привязкой к golden tests.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/duration.py"

## DoD
- [ ] Функции `compute_sojourn_time(df) -> df`, `compute_own_duration(df) -> Series`, `compute_case_duration(df) -> df` в `app/domain/mining/duration.py`.
- [ ] Golden test: для топ-10 операций средняя/медиана/p90 sojourn совпадает с `expected_metrics.json["sojourn_time_top10_operations"]`.
- [ ] Unit-тесты на пограничные случаи.

## Реализация — псевдокод в `02_DOMAIN_LOGIC.md`.

## Тесты
- `test_sojourn_first_event_equals_own_duration`.
- `test_sojourn_subsequent_event_from_prev_completed`.
- `test_sojourn_independent_per_case`.
- Golden test `test_sojourn_top10` из `06_TESTING.md`.

## Acceptance
Golden test для sojourn зелёный.
