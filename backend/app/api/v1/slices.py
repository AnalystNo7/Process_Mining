from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import EntityNotFoundError
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.slices import SliceCreate, SliceList, SliceResponse, SliceUpdate
from app.services import slice_service

router = APIRouter(
    prefix="/projects/{project_id}/virtual-datasets/{vd_id}/slices",
    tags=["Срезы"],
)


@router.get("", response_model=SliceList)
async def list_slices(
    project_id: int,
    vd_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SliceList:
    items, total = await slice_service.list_slices(db, vd_id)
    return SliceList(
        items=[SliceResponse.model_validate(s) for s in items], total=total
    )


@router.post("", response_model=SliceResponse, status_code=status.HTTP_201_CREATED)
async def create_slice(
    project_id: int,
    vd_id: int,
    payload: SliceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SliceResponse:
    try:
        named_slice = await slice_service.create_slice(db, vd_id, payload, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return SliceResponse.model_validate(named_slice)


@router.patch("/{slice_id}", response_model=SliceResponse)
async def update_slice(
    project_id: int,
    vd_id: int,
    slice_id: int,
    payload: SliceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SliceResponse:
    try:
        named_slice = await slice_service.update_slice(db, slice_id, payload, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return SliceResponse.model_validate(named_slice)


@router.delete("/{slice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slice(
    project_id: int,
    vd_id: int,
    slice_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await slice_service.delete_slice(db, slice_id, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
