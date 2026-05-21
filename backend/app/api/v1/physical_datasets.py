from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_project_owner_or_admin
from app.core.exceptions import ConflictError, EntityNotFoundError
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.physical_datasets import (
    PhysicalDatasetCreate,
    PhysicalDatasetList,
    PhysicalDatasetResponse,
    PreviewResponse,
    UploadTaskResponse,
)
from app.services import physical_dataset_service
from app.tasks.upload import upload_dataset_task

router = APIRouter(
    prefix="/projects/{project_id}/physical-datasets", tags=["Физические датасеты"]
)


@router.post("/preview", response_model=PreviewResponse)
async def preview_dataset(
    file: UploadFile = File(...),
    _project: Project = Depends(require_project_owner_or_admin),
) -> PreviewResponse:
    return await physical_dataset_service.preview_upload(file)


@router.post("", response_model=UploadTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_dataset(
    project_id: int,
    payload: PhysicalDatasetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(require_project_owner_or_admin),
    user: User = Depends(get_current_user),
) -> UploadTaskResponse:
    try:
        dataset = await physical_dataset_service.create_physical_dataset(
            db, project_id, payload, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    task = upload_dataset_task.delay(dataset.id)
    return UploadTaskResponse(id=dataset.id, status=dataset.status, task_id=task.id)


@router.get("", response_model=PhysicalDatasetList)
async def list_datasets(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PhysicalDatasetList:
    items, total = await physical_dataset_service.list_physical_datasets(db, project_id)
    return PhysicalDatasetList(
        items=[PhysicalDatasetResponse.model_validate(d) for d in items], total=total
    )


@router.get("/{dataset_id}", response_model=PhysicalDatasetResponse)
async def get_dataset(
    project_id: int,
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PhysicalDatasetResponse:
    try:
        dataset = await physical_dataset_service.get_physical_dataset(
            db, project_id, dataset_id
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return PhysicalDatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    project_id: int,
    dataset_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(require_project_owner_or_admin),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await physical_dataset_service.delete_physical_dataset(
            db, project_id, dataset_id, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
