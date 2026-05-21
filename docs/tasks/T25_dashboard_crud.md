# T25: CRUD дашбордов

## Цель
API + базовый UI для создания, редактирования, удаления дашбордов с виджетами.

## Контекст
- `01_DATA_MODEL.md` таблицы `core.dashboards`, `core.dashboard_widgets`
- `03_API.md` разделы "11. Дашборды", "12. Виджеты"
- `04_UI.md` раздел "10. Дашборд"

## DoD
- [ ] Эндпоинты: `GET/POST /virtual-datasets/{id}/dashboards`, `GET/PATCH/DELETE /dashboards/{id}`, `POST /dashboards/{id}/duplicate`, `POST/PATCH/DELETE /dashboards/{id}/widgets`.
- [ ] При создании виртуального датасета — автоматически создаётся дефолтный дашборд "Обзор процесса" с предустановленными виджетами:
  - 4 KPI-карточки: total_cases, total_events, global_rework_pct, avg_case_duration
  - 1 rework_table (top-25)
  - 1 monthly_dynamics
  - 1 top_paths_graph (n=5)
- [ ] UI: страница `/virtual/:vdId/dashboards/:dashId` со списком виджетов в read-only mode.
- [ ] Кнопка `Редактировать` переключает на edit-mode с drag&drop (см. T30).

## Реализация

### Дефолтный дашборд при создании VD
```python
async def create_default_dashboard(db: AsyncSession, vd: VirtualDataset, user: User):
    dash = Dashboard(
        virtual_dataset_id=vd.id,
        name="Обзор процесса",
        description="Автоматически созданный обзорный дашборд",
        layout=[],
        created_by=user.id,
    )
    db.add(dash)
    await db.flush()
    
    widgets_config = [
        {"widget_type": "kpi_card", "title": "Всего кейсов",
         "config": {"metric": "total_cases", "format": "number"},
         "grid_x": 0, "grid_y": 0, "grid_width": 3, "grid_height": 2},
        {"widget_type": "kpi_card", "title": "Всего операций",
         "config": {"metric": "total_events", "format": "number"},
         "grid_x": 3, "grid_y": 0, "grid_width": 3, "grid_height": 2},
        {"widget_type": "kpi_card", "title": "% повторов",
         "config": {"metric": "global_rework_pct", "format": "percent"},
         "grid_x": 6, "grid_y": 0, "grid_width": 3, "grid_height": 2},
        {"widget_type": "kpi_card", "title": "Средняя длительность",
         "config": {"metric": "avg_case_duration_seconds", "format": "duration"},
         "grid_x": 9, "grid_y": 0, "grid_width": 3, "grid_height": 2},
        {"widget_type": "monthly_dynamics", "title": "Динамика по месяцам",
         "config": {"show_avg_sojourn_line": True},
         "grid_x": 0, "grid_y": 2, "grid_width": 12, "grid_height": 4},
        {"widget_type": "rework_table", "title": "Топ повторов",
         "config": {"limit": 25, "activity_level": "raw"},
         "grid_x": 0, "grid_y": 6, "grid_width": 6, "grid_height": 4},
        {"widget_type": "top_paths_graph", "title": "Топ-5 путей процесса",
         "config": {"n_paths": 5, "activity_level": "role"},
         "grid_x": 6, "grid_y": 6, "grid_width": 6, "grid_height": 4},
    ]
    
    for w in widgets_config:
        db.add(DashboardWidget(dashboard_id=dash.id, **w))
    
    await db.commit()
```

Вызвать это в T15 (создание VD) после создания VD.

## Тесты
- `test_create_vd_creates_default_dashboard`.
- `test_dashboard_crud`.
- `test_duplicate_dashboard_copies_all_widgets`.

## Acceptance
После создания VD автоматически открывается дашборд с базовыми виджетами (хотя пока без данных — see T26-T29).
