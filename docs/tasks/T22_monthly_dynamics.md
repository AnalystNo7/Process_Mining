# T22: Динамика по месяцам

## Цель
Combined chart "Кол-во операций (бары) + средняя длительность с учётом перехода (линия)" по месяцам.

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "domain/mining/dynamics.py"
- Слайды Газпрома 6, 11, 16, 21, 22 — образец

## DoD
- [ ] Функция `compute_monthly_dynamics(df, activity_filter=None)`.
- [ ] Эндпоинт `GET /analytics/monthly-dynamics` с опц. `?activity=`.
- [ ] Группировка по месяцу start (МСК).
- [ ] Возвращает: month, n_events, n_cases, avg_sojourn_seconds.
- [ ] Unit-тест: данные за 3 месяца → 3 строки.

## Реализация — псевдокод в `02_DOMAIN_LOGIC.md`.

## Acceptance
Endpoint возвращает данные. На UI график рисуется (плагин виджет см. T27).
