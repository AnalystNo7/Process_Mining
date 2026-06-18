from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from typing import Any

from app.core.exceptions import (
    BusinessRuleError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from app.db.models.dashboards import Dashboard, DashboardWidget
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.dashboards import (
    DashboardBrief,
    DashboardCreate,
    DashboardLayoutUpdate,
    DashboardList,
    DashboardResponse,
    DashboardUpdate,
    WidgetCreate,
    WidgetResponse,
    WidgetUpdate,
)
from app.services import dashboard_service, widget_data_service

router = APIRouter(tags=["Дашборды"])


def _to_response(
    dashboard: Dashboard, widgets: list[DashboardWidget]
) -> DashboardResponse:
    return DashboardResponse(
        id=dashboard.id,
        virtual_dataset_id=dashboard.virtual_dataset_id,
        name=dashboard.name,
        description=dashboard.description,
        global_filters=dashboard.global_filters,
        applied_slice_id=dashboard.applied_slice_id,
        layout=dashboard.layout,
        template_kind=dashboard.template_kind,
        created_by=dashboard.created_by,
        created_at=dashboard.created_at,
        widgets=[WidgetResponse.model_validate(w) for w in widgets],
    )


@router.post(
    "/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dashboard(
    project_id: int,
    vd_id: int,
    payload: DashboardCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardResponse:
    try:
        dashboard = await dashboard_service.create_dashboard(
            db, vd_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _to_response(dashboard, [])


@router.get(
    "/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
    response_model=DashboardList,
)
async def list_dashboards(
    project_id: int,
    vd_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> DashboardList:
    items, total = await dashboard_service.list_dashboards(db, vd_id)
    return DashboardList(
        items=[DashboardBrief.model_validate(d) for d in items], total=total
    )


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> DashboardResponse:
    try:
        dashboard, widgets = await dashboard_service.get_dashboard(db, dashboard_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _to_response(dashboard, widgets)


@router.patch("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    payload: DashboardUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardResponse:
    try:
        await dashboard_service.update_dashboard(db, dashboard_id, payload, user, request)
        dashboard, widgets = await dashboard_service.get_dashboard(db, dashboard_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    return _to_response(dashboard, widgets)


@router.patch(
    "/dashboards/{dashboard_id}/widgets/layout",
    response_model=DashboardResponse,
)
async def update_widget_layouts(
    dashboard_id: int,
    payload: DashboardLayoutUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardResponse:
    """Batch-обновление координат виджетов после drag/resize."""
    try:
        await dashboard_service.update_widget_layouts(
            db, dashboard_id, payload, user, request
        )
        dashboard, widgets = await dashboard_service.get_dashboard(db, dashboard_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return _to_response(dashboard, widgets)


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await dashboard_service.delete_dashboard(db, dashboard_id, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc


@router.post(
    "/dashboards/{dashboard_id}/duplicate",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_dashboard(
    dashboard_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardResponse:
    try:
        copy = await dashboard_service.duplicate_dashboard(db, dashboard_id, user, request)
        dashboard, widgets = await dashboard_service.get_dashboard(db, copy.id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _to_response(dashboard, widgets)


@router.post(
    "/dashboards/{dashboard_id}/widgets",
    response_model=WidgetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_widget(
    dashboard_id: int,
    payload: WidgetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WidgetResponse:
    try:
        widget = await dashboard_service.add_widget(
            db, dashboard_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    return WidgetResponse.model_validate(widget)


@router.get("/widgets/{widget_id}/data")
async def get_widget_data(
    widget_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Рассчитанные данные для отрисовки виджета (форма зависит от типа)."""
    try:
        widget = await dashboard_service.get_widget(db, widget_id)
        return await widget_data_service.compute_widget_data(db, widget)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.patch("/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    widget_id: int,
    payload: WidgetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WidgetResponse:
    try:
        widget = await dashboard_service.update_widget(
            db, widget_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    return WidgetResponse.model_validate(widget)


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await dashboard_service.delete_widget(db, widget_id, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
