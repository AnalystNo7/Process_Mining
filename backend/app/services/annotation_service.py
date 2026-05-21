"""Аннотации виртуального датасета (см. 04_UI.md, T36).

Примечание по хранению: 01_DATA_MODEL.md задаёт колонку annotations.target_id
как VARCHAR(500), а T36 — структурированный объект target. Объект сохраняется
JSON-сериализованным в той же колонке: схема БД не меняется, контракт T36
по API соблюдён."""

import json
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.db.models.dashboards import Annotation
from app.db.models.datasets import VirtualDataset
from app.db.models.users import User
from app.schemas.annotations import AnnotationCreate, AnnotationUpdate
from app.services import audit_service


def encode_target(target: dict[str, Any]) -> str:
    return json.dumps(target, sort_keys=True, ensure_ascii=False)


def decode_target(raw: str) -> dict[str, Any]:
    target: dict[str, Any] = json.loads(raw)
    return target


async def _ensure_vd_exists(db: AsyncSession, vd_id: int) -> None:
    if await db.get(VirtualDataset, vd_id) is None:
        raise EntityNotFoundError(f"Виртуальный датасет с id={vd_id} не найден")


async def author_names(db: AsyncSession, annotations: list[Annotation]) -> dict[int, str]:
    """Сопоставляет id авторов с отображаемыми именами одним запросом."""
    ids = {a.created_by for a in annotations}
    if not ids:
        return {}
    users = (await db.scalars(select(User).where(User.id.in_(ids)))).all()
    return {u.id: (u.full_name or u.username) for u in users}


async def author_name(db: AsyncSession, user_id: int) -> str:
    user = await db.get(User, user_id)
    if user is None:
        return "—"
    return user.full_name or user.username


async def list_annotations(
    db: AsyncSession, vd_id: int, *, target_type: str | None = None
) -> list[Annotation]:
    await _ensure_vd_exists(db, vd_id)
    conditions = [Annotation.virtual_dataset_id == vd_id]
    if target_type is not None:
        conditions.append(Annotation.target_type == target_type)
    stmt = (
        select(Annotation)
        .where(*conditions)
        .order_by(Annotation.created_at, Annotation.id)
    )
    return list((await db.scalars(stmt)).all())


async def get_annotation(db: AsyncSession, annotation_id: int) -> Annotation:
    annotation = await db.get(Annotation, annotation_id)
    if annotation is None:
        raise EntityNotFoundError(f"Аннотация с id={annotation_id} не найдена")
    return annotation


def _ensure_can_modify(annotation: Annotation, actor: User) -> None:
    if actor.role != "admin" and annotation.created_by != actor.id:
        raise PermissionDeniedError(
            "Редактировать аннотацию может только её автор или администратор"
        )


async def create_annotation(
    db: AsyncSession,
    vd_id: int,
    data: AnnotationCreate,
    actor: User,
    request: Request | None = None,
) -> Annotation:
    await _ensure_vd_exists(db, vd_id)
    annotation = Annotation(
        virtual_dataset_id=vd_id,
        target_type=data.target_type,
        target_id=encode_target(data.target),
        text=data.text,
        color=data.color,
        created_by=actor.id,
    )
    db.add(annotation)
    await db.flush()
    await audit_service.log_event(
        db, actor, "annotation.create", "annotation", annotation.id, request=request
    )
    await db.commit()
    await db.refresh(annotation)
    return annotation


async def update_annotation(
    db: AsyncSession,
    annotation_id: int,
    data: AnnotationUpdate,
    actor: User,
    request: Request | None = None,
) -> Annotation:
    annotation = await get_annotation(db, annotation_id)
    _ensure_can_modify(annotation, actor)
    annotation.text = data.text
    await audit_service.log_event(
        db, actor, "annotation.update", "annotation", annotation_id, request=request
    )
    await db.commit()
    await db.refresh(annotation)
    return annotation


async def delete_annotation(
    db: AsyncSession, annotation_id: int, actor: User, request: Request | None = None
) -> None:
    annotation = await get_annotation(db, annotation_id)
    _ensure_can_modify(annotation, actor)
    await db.delete(annotation)
    await audit_service.log_event(
        db, actor, "annotation.delete", "annotation", annotation_id, request=request
    )
    await db.commit()
