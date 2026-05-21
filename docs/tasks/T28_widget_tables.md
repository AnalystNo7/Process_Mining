# T28: Виджеты rework_table, resource_analysis_table, sla_compliance_table

## Цель
Все табличные виджеты на AntD `Table`.

## Контекст
- `04_UI.md` каталог виджетов

## DoD
- [ ] Backend `compute_rework_table`, `compute_resource_analysis_table` (T35 для sla).
- [ ] Frontend компоненты с AntD Table, сортировка/фильтр в шапке, пагинация.
- [ ] Поддержка highlight_threshold_pct в rework_table (подсветка >threshold).
- [ ] Drill-down: клик на строку → emit event (для T32).

## Реализация
### rework_table
- Backend использует T19 функции.
- Frontend: AntD Table со столбцами: Операция, Кол-во, Повторов, % rework. Подсветка >30% (красная), 15-30% (жёлтая), <15% (нейтральная).

### resource_analysis_table
- Backend использует T23.
- Колонки: Исполнитель, Кейсов, Событий, Ср.длительность операций, Уник.операций.

## Acceptance
Таблицы на дашборде synthetic_log выглядят как соответствующие слайды Газпрома (7, 12, 17, 24).
