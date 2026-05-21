from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.db.models.datasets import NamedSlice, VirtualDataset
from app.db.models.users import User
from app.schemas.slices import SliceCreate, SliceUpdate
from app.services import audit_service


async def list_slices(db: AsyncSession, vd_id: int) -> tuple[list[NamedSlice], int]:
    stmt = (
        select(NamedSlice)
        .where(NamedSlice.virtual_dataset_id == vd_id)
        .order_by(NamedSlice.created_at)
    )
    items = list((await db.scalars(stmt)).all())
    return items, len(items)


async def get_slice(db: AsyncSession, slice_id: int) -> NamedSlice:
    named_slice = await db.get(NamedSlice, slice_id)
    if named_slice is None:
        raise EntityNotFoundError(f"Срез с id={slice_id} не найден")
    return named_slice


async def create_slice(
    db: AsyncSession,
    vd_id: int,
    data: SliceCreate,
    actor: User,
    request: Request | None = None,
) -> NamedSlice:
    virtual = await db.get(VirtualDataset, vd_id)
    if virtual is None:
        raise EntityNotFoundError(f"Виртуальный датасет с id={vd_id} не найден")
    named_slice = NamedSlice(
        virtual_dataset_id=vd_id,
        name=data.name,
        description=data.description,
        filters=data.filters,
        created_by=actor.id,
    )
    db.add(named_slice)
    await db.flush()
    await audit_service.log_event(
        db, actor, "slice.create", "named_slice", named_slice.id, request=request
    )
    await db.commit()
    await db.refresh(named_slice)
    return named_slice


async def update_slice(
    db: AsyncSession,
    slice_id: int,
    data: SliceUpdate,
    actor: User,
    request: Request | None = None,
) -> NamedSlice:
    named_slice = await get_slice(db, slice_id)
    if data.name is not None:
        named_slice.name = data.name
    if data.description is not None:
        named_slice.description = data.description
    if data.filters is not None:
        named_slice.filters = data.filters
    await audit_service.log_event(
        db, actor, "slice.update", "named_slice", slice_id, request=request
    )
    await db.commit()
    await db.refresh(named_slice)
    return named_slice


async def delete_slice(
    db: AsyncSession, slice_id: int, actor: User, request: Request | None = None
) -> None:
    """Удаляет срез. FK dashboards.applied_slice_id (ON DELETE SET NULL)
    автоматически сбрасывается — дашборды не ломаются."""
    named_slice = await get_slice(db, slice_id)
    await db.delete(named_slice)
    await audit_service.log_event(
        db, actor, "slice.delete", "named_slice", slice_id, request=request
    )
    await db.commit()
