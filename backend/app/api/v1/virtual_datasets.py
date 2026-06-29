from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import (
    BusinessRuleError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.virtual_datasets import (
    ActivityBreakdownResponse,
    ApplyMappingResponse,
    RoleBreakdownResponse,
    ViewModeUpdate,
    VirtualDatasetBrief,
    VirtualDatasetCreate,
    VirtualDatasetList,
    VirtualDatasetResponse,
)
from app.services import virtual_dataset_service

router = APIRouter(
    prefix="/projects/{project_id}/virtual-datasets", tags=["Виртуальные датасеты"]
)


@router.post("", response_model=VirtualDatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_virtual_dataset(
    project_id: int,
    payload: VirtualDatasetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VirtualDatasetResponse:
    try:
        virtual = await virtual_dataset_service.create_virtual_dataset(
            db, project_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return VirtualDatasetResponse.model_validate(virtual)


@router.get("", response_model=VirtualDatasetList)
async def list_virtual_datasets(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> VirtualDatasetList:
    items, total = await virtual_dataset_service.list_virtual_datasets(db, project_id)
    return VirtualDatasetList(
        items=[VirtualDatasetBrief.model_validate(v) for v in items], total=total
    )


@router.get("/{vd_id}", response_model=VirtualDatasetResponse)
async def get_virtual_dataset(
    project_id: int,
    vd_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> VirtualDatasetResponse:
    try:
        virtual = await virtual_dataset_service.get_virtual_dataset(db, project_id, vd_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return VirtualDatasetResponse.model_validate(virtual)


@router.patch("/{vd_id}/view-mode", response_model=VirtualDatasetResponse)
async def set_view_mode(
    project_id: int,
    vd_id: int,
    payload: ViewModeUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VirtualDatasetResponse:
    """Глобальный переключатель отображения операций (raw|role) для всего
    датасета — перестраивает все его дашборды и аналитику."""
    try:
        virtual = await virtual_dataset_service.set_view_mode(
            db, project_id, vd_id, payload.activity_level, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return VirtualDatasetResponse.model_validate(virtual)


@router.post("/apply-mapping-view", response_model=ApplyMappingResponse)
async def apply_mapping_to_view(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplyMappingResponse:
    """Применяет текущую разметку ролей проекта к отображению всех его
    виртуальных датасетов (обновляет снимок и включает режим role)."""
    try:
        updated = await virtual_dataset_service.apply_mapping_to_view(
            db, project_id, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return ApplyMappingResponse(updated_virtual_datasets=updated)


@router.delete("/{vd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_dataset(
    project_id: int,
    vd_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await virtual_dataset_service.delete_virtual_dataset(
            db, project_id, vd_id, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc


@router.get("/{vd_id}/role-breakdown", response_model=RoleBreakdownResponse)
async def get_role_breakdown(
    project_id: int,
    vd_id: int,
    role: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RoleBreakdownResponse:
    try:
        return await virtual_dataset_service.role_breakdown(db, project_id, vd_id, role)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{vd_id}/activity-breakdown", response_model=ActivityBreakdownResponse)
async def get_activity_breakdown(
    project_id: int,
    vd_id: int,
    activity_with_role: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ActivityBreakdownResponse:
    try:
        return await virtual_dataset_service.activity_breakdown(
            db, project_id, vd_id, activity_with_role
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
