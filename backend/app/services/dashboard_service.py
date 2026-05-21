from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.db.models.dashboards import Dashboard, DashboardWidget
from app.db.models.datasets import VirtualDataset
from app.db.models.users import User
from app.schemas.dashboards import DashboardCreate, DashboardUpdate, WidgetCreate, WidgetUpdate
from app.services import audit_service

# Виджеты дашборда «Обзор процесса», создаётся автоматически при создании
# виртуального датасета (см. T25).
_DEFAULT_WIDGETS: list[dict[str, Any]] = [
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


async def create_default_dashboard(
    db: AsyncSession, virtual: VirtualDataset, actor: User
) -> Dashboard:
    """Создаёт дашборд «Обзор процесса» с предустановленными виджетами.
    Commit выполняет вызывающий код."""
    dashboard = Dashboard(
        virtual_dataset_id=virtual.id,
        name="Обзор процесса",
        description="Автоматически созданный обзорный дашборд",
        layout=[],
        created_by=actor.id,
    )
    db.add(dashboard)
    await db.flush()
    for widget_cfg in _DEFAULT_WIDGETS:
        db.add(DashboardWidget(dashboard_id=dashboard.id, **widget_cfg))
    return dashboard


async def _get_widgets(db: AsyncSession, dashboard_id: int) -> list[DashboardWidget]:
    stmt = (
        select(DashboardWidget)
        .where(DashboardWidget.dashboard_id == dashboard_id)
        .order_by(DashboardWidget.grid_y, DashboardWidget.grid_x, DashboardWidget.id)
    )
    return list((await db.scalars(stmt)).all())


async def get_dashboard(
    db: AsyncSession, dashboard_id: int
) -> tuple[Dashboard, list[DashboardWidget]]:
    dashboard = await db.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise EntityNotFoundError(f"Дашборд с id={dashboard_id} не найден")
    return dashboard, await _get_widgets(db, dashboard_id)


async def _require_owner(dashboard: Dashboard, actor: User) -> None:
    if actor.role != "admin" and dashboard.created_by != actor.id:
        raise PermissionDeniedError(
            "Изменять дашборд может только его создатель или администратор"
        )


async def list_dashboards(
    db: AsyncSession, vd_id: int
) -> tuple[list[Dashboard], int]:
    stmt = (
        select(Dashboard)
        .where(Dashboard.virtual_dataset_id == vd_id)
        .order_by(Dashboard.created_at)
    )
    items = list((await db.scalars(stmt)).all())
    return items, len(items)


async def create_dashboard(
    db: AsyncSession,
    vd_id: int,
    data: DashboardCreate,
    actor: User,
    request: Request | None = None,
) -> Dashboard:
    virtual = await db.get(VirtualDataset, vd_id)
    if virtual is None:
        raise EntityNotFoundError(f"Виртуальный датасет с id={vd_id} не найден")
    dashboard = Dashboard(
        virtual_dataset_id=vd_id,
        name=data.name,
        description=data.description,
        global_filters=data.global_filters,
        applied_slice_id=data.applied_slice_id,
        layout=data.layout,
        created_by=actor.id,
    )
    db.add(dashboard)
    await db.flush()
    await audit_service.log_event(
        db, actor, "dashboard.create", "dashboard", dashboard.id, request=request
    )
    await db.commit()
    await db.refresh(dashboard)
    return dashboard


async def update_dashboard(
    db: AsyncSession,
    dashboard_id: int,
    data: DashboardUpdate,
    actor: User,
    request: Request | None = None,
) -> Dashboard:
    dashboard, _ = await get_dashboard(db, dashboard_id)
    await _require_owner(dashboard, actor)
    if data.name is not None:
        dashboard.name = data.name
    if data.description is not None:
        dashboard.description = data.description
    if data.global_filters is not None:
        dashboard.global_filters = data.global_filters
    if data.applied_slice_id is not None:
        dashboard.applied_slice_id = data.applied_slice_id
    if data.layout is not None:
        dashboard.layout = data.layout
    await audit_service.log_event(
        db, actor, "dashboard.update", "dashboard", dashboard_id, request=request
    )
    await db.commit()
    await db.refresh(dashboard)
    return dashboard


async def delete_dashboard(
    db: AsyncSession, dashboard_id: int, actor: User, request: Request | None = None
) -> None:
    dashboard, _ = await get_dashboard(db, dashboard_id)
    await _require_owner(dashboard, actor)
    await db.delete(dashboard)
    await audit_service.log_event(
        db, actor, "dashboard.delete", "dashboard", dashboard_id, request=request
    )
    await db.commit()


async def duplicate_dashboard(
    db: AsyncSession, dashboard_id: int, actor: User, request: Request | None = None
) -> Dashboard:
    source, widgets = await get_dashboard(db, dashboard_id)
    copy = Dashboard(
        virtual_dataset_id=source.virtual_dataset_id,
        name=f"{source.name} (копия)",
        description=source.description,
        global_filters=dict(source.global_filters),
        applied_slice_id=source.applied_slice_id,
        layout=list(source.layout),
        created_by=actor.id,
    )
    db.add(copy)
    await db.flush()
    for widget in widgets:
        db.add(
            DashboardWidget(
                dashboard_id=copy.id,
                widget_type=widget.widget_type,
                title=widget.title,
                config=dict(widget.config),
                local_filters=widget.local_filters,
                use_global_filters=widget.use_global_filters,
                grid_x=widget.grid_x,
                grid_y=widget.grid_y,
                grid_width=widget.grid_width,
                grid_height=widget.grid_height,
            )
        )
    await audit_service.log_event(
        db, actor, "dashboard.create", "dashboard", copy.id, request=request,
        metadata={"duplicated_from": dashboard_id},
    )
    await db.commit()
    await db.refresh(copy)
    return copy


async def add_widget(
    db: AsyncSession,
    dashboard_id: int,
    data: WidgetCreate,
    actor: User,
    request: Request | None = None,
) -> DashboardWidget:
    dashboard, _ = await get_dashboard(db, dashboard_id)
    await _require_owner(dashboard, actor)
    widget = DashboardWidget(dashboard_id=dashboard_id, **data.model_dump())
    db.add(widget)
    await audit_service.log_event(
        db, actor, "dashboard.update", "dashboard", dashboard_id, request=request,
        metadata={"action": "add_widget"},
    )
    await db.commit()
    await db.refresh(widget)
    return widget


async def get_widget(db: AsyncSession, widget_id: int) -> DashboardWidget:
    widget = await db.get(DashboardWidget, widget_id)
    if widget is None:
        raise EntityNotFoundError(f"Виджет с id={widget_id} не найден")
    return widget


async def update_widget(
    db: AsyncSession,
    widget_id: int,
    data: WidgetUpdate,
    actor: User,
    request: Request | None = None,
) -> DashboardWidget:
    widget = await get_widget(db, widget_id)
    dashboard, _ = await get_dashboard(db, widget.dashboard_id)
    await _require_owner(dashboard, actor)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(widget, field, value)
    await db.commit()
    await db.refresh(widget)
    return widget


async def delete_widget(
    db: AsyncSession, widget_id: int, actor: User, request: Request | None = None
) -> None:
    widget = await get_widget(db, widget_id)
    dashboard, _ = await get_dashboard(db, widget.dashboard_id)
    await _require_owner(dashboard, actor)
    await db.delete(widget)
    await db.commit()
