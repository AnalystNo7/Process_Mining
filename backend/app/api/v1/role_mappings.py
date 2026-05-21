from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_project_owner_or_admin
from app.core.exceptions import EntityNotFoundError
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.role_mappings import (
    RoleMappingHistoryItem,
    RoleMappingResponse,
    RoleMappingUpdate,
    SuggestRequest,
    SuggestResponse,
)
from app.services import role_mapping_service

router = APIRouter(prefix="/projects/{project_id}/role-mappings", tags=["Маппинг ролей"])


@router.get("/current", response_model=RoleMappingResponse)
async def get_current(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RoleMappingResponse:
    try:
        mapping = await role_mapping_service.get_current_mapping(db, project_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return RoleMappingResponse.model_validate(mapping)


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_roles(
    project_id: int,
    payload: SuggestRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SuggestResponse:
    suggestions, available_roles = await role_mapping_service.suggest(
        db, payload.departments
    )
    return SuggestResponse(suggestions=suggestions, available_roles=available_roles)


@router.put("/current", response_model=RoleMappingResponse)
async def update_current(
    project_id: int,
    payload: RoleMappingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(require_project_owner_or_admin),
    user: User = Depends(get_current_user),
) -> RoleMappingResponse:
    try:
        mapping = await role_mapping_service.update_mapping(
            db, project_id, payload.mapping, payload.roles, user, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return RoleMappingResponse.model_validate(mapping)


@router.get("/history", response_model=list[RoleMappingHistoryItem])
async def get_history(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[RoleMappingHistoryItem]:
    versions = await role_mapping_service.get_history(db, project_id)
    return [RoleMappingHistoryItem.model_validate(v) for v in versions]
