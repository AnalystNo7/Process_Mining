# T13: Health Check датасета

## Цель
Проверка пригодности загруженного датасета для анализа с цветовой меткой (good/warning/poor) и подробным отчётом.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Модуль domain/mining/health.py"

## DoD
- [ ] Функция `health_check(df) -> HealthReport` в `app/domain/mining/health.py`.
- [ ] Реализованы все 5 проверок: cases_count, events_per_case, rework_pct, department_field, resource_field.
- [ ] Возвращается dataclass `HealthReport(status, checks)`.
- [ ] Сохраняется в `physical_datasets.health_report` и `health_status` после загрузки.
- [ ] Эндпоинт `GET /physical-datasets/{id}/health` возвращает текущий отчёт.
- [ ] UI показывает health на странице деталей физ.датасета: цветной Tag + раскрывающийся список проверок.

## Реализация — см. полный псевдокод в `02_DOMAIN_LOGIC.md`

## Тесты
- `test_health_good_on_synthetic_log` — на нашем golden датасете должен быть warning (т.к. 46% нулевых длительностей).
- `test_health_poor_on_small_dataset` (10 кейсов).
- `test_health_warning_on_low_rework`.

## Acceptance
После загрузки synthetic_log.xlsx в UI видны цветные метки health с конкретными числами (1328 cases, 20% rework).
