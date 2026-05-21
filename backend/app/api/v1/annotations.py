from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.db.models.dashboards import Annotation
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.annotations import (
    AnnotationCreate,
    AnnotationList,
    AnnotationResponse,
    AnnotationTargetType,
    AnnotationUpdate,
)
from app.services import annotation_service

router = APIRouter(tags=["Аннотации"])


def _to_response(annotation: Annotation, author: str) -> AnnotationResponse:
    return AnnotationResponse(
        id=annotation.id,
        virtual_dataset_id=annotation.virtual_dataset_id,
        target_type=annotation.target_type,
        target=annotation_service.decode_target(annotation.target_id),
        text=annotation.text,
        color=annotation.color,
        author_id=annotation.created_by,
        author_name=author,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


@router.get(
    "/virtual-datasets/{vd_id}/annotations", response_model=AnnotationList
)
async def list_annotations(
    vd_id: int,
    target_type: AnnotationTargetType | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> AnnotationList:
    try:
        items = await annotation_service.list_annotations(
            db, vd_id, target_type=target_type
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    authors = await annotation_service.author_names(db, items)
    return AnnotationList(
        items=[_to_response(a, authors.get(a.created_by, "—")) for a in items],
        total=len(items),
    )


@router.post(
    "/virtual-datasets/{vd_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(
    vd_id: int,
    payload: AnnotationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnnotationResponse:
    try:
        annotation = await annotation_service.create_annotation(
            db, vd_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return _to_response(annotation, user.full_name or user.username)


@router.put("/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: int,
    payload: AnnotationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnnotationResponse:
    try:
        annotation = await annotation_service.update_annotation(
            db, annotation_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    author = await annotation_service.author_name(db, annotation.created_by)
    return _to_response(annotation, author)


@router.delete(
    "/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_annotation(
    annotation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await annotation_service.delete_annotation(db, annotation_id, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
