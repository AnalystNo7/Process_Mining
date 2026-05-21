# T19: Метрики rework (ping-pong)

## Цель
Чистые функции для ping-pong анализа: повторы операций, % rework, сравнение длительности.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/rework.py"

## DoD
- [ ] Функции `compute_rework_per_operation`, `compute_global_rework_pct`, `split_cases_by_rework`, `compute_duration_comparison`.
- [ ] Эндпоинт `GET /virtual-datasets/{id}/analytics/rework-table` использует эти функции через event_log_repo.load_to_dataframe + apply_role_mapping + apply_filter.
- [ ] Поддержка activity_level=raw|role: для role используется колонка `activity_with_role`.
- [ ] Golden tests все зелёные:
  - global_rework_pct == 20.06% (±1%)
  - n_cases_with_rework == 1145
  - top-10 operations совпадают (точно по total/repeats, ±0.05% по rework_pct).

## Реализация — см. полный псевдокод в `02_DOMAIN_LOGIC.md`.

## Тесты
- Unit-тесты на простых DataFrame'ах.
- Golden tests из `06_TESTING.md`.

## Acceptance
Запрос `GET /analytics/rework-table?activity_level=raw` на synthetic_log возвращает топ-10, совпадающий с golden.
