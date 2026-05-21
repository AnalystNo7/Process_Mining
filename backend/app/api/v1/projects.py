from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_project_owner_or_admin
from app.core.exceptions import EntityNotFoundError
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.projects import (
    ProjectCreate,
    ProjectList,
    ProjectResponse,
    ProjectUpdate,
    UserBriefResponse,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Проекты"])


def _to_response(
    project: Project, owner: User, counts: tuple[int, int, int]
) -> ProjectResponse:
    physical, virtual, dashboards = counts
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_by=UserBriefResponse.model_validate(owner),
        created_at=project.created_at,
        physical_datasets_count=physical,
        virtual_datasets_count=virtual,
        dashboards_count=dashboards,
    )


@router.get("", response_model=ProjectList)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    search: str | None = None,
    created_by: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ProjectList:
    rows, total = await project_service.list_projects(
        db, page=page, page_size=page_size, search=search, created_by=created_by
    )
    counts = await project_service.project_counts(db, [project.id for project, _ in rows])
    items = [
        _to_response(project, owner, counts.get(project.id, (0, 0, 0)))
        for project, owner in rows
    ]
    return ProjectList(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await project_service.create_project(db, payload, user, request)
    return _to_response(project, user, (0, 0, 0))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ProjectResponse:
    try:
        project, owner = await project_service.get_project_with_owner(db, project_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    counts = await project_service.project_counts(db, [project.id])
    return _to_response(project, owner, counts.get(project.id, (0, 0, 0)))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    payload: ProjectUpdate,
    request: Request,
    project: Project = Depends(require_project_owner_or_admin),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    await project_service.update_project(db, project, payload, user, request)
    updated, owner = await project_service.get_project_with_owner(db, project.id)
    counts = await project_service.project_counts(db, [updated.id])
    return _to_response(updated, owner, counts.get(updated.id, (0, 0, 0)))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    request: Request,
    project: Project = Depends(require_project_owner_or_admin),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await project_service.delete_project(db, project, user, request)
