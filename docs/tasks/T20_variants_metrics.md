# T20: Варианты процесса и пути

## Цель
ТОП-N путей процесса, вариативность путей, встречаемость операций.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/variants.py"

## DoD
- [ ] Функции `get_case_traces`, `get_top_n_variants`, `get_variants_coverage`, `compute_variability_pct`, `compute_mean_occurrence_pct`.
- [ ] Эндпоинт `GET /virtual-datasets/{id}/analytics/top-paths`.
- [ ] Golden tests:
  - variability_pct == 89.83% (±0.05%)
  - mean_occurrence_pct == 3.04% (±0.05%)
  - unique_traces == 1194.

## Реализация — см. `02_DOMAIN_LOGIC.md`.

## Тесты
- Unit-тест: 3 кейса с разными трассами → variability 100%.
- Unit-тест: 5 кейсов с одинаковой трассой → variability 20%.
- Golden tests.

## Acceptance
Golden tests зелёные. UI показывает корректные KPI variability и mean_occurrence.
