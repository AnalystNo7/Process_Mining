from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.exceptions import BusinessRuleError, EntityNotFoundError
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.global_roles import (
    GlobalRoleTemplateCreate,
    GlobalRoleTemplateList,
    GlobalRoleTemplateResponse,
    GlobalRoleTemplateUpdate,
)
from app.services import global_role_service

router = APIRouter(prefix="/admin/global-role-templates", tags=["Глобальные роли"])


@router.get("", response_model=GlobalRoleTemplateList)
async def list_global_role_templates(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> GlobalRoleTemplateList:
    items = await global_role_service.list_templates(db)
    return GlobalRoleTemplateList(
        items=[GlobalRoleTemplateResponse.model_validate(t) for t in items],
        total=len(items),
    )


@router.post(
    "",
    response_model=GlobalRoleTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_global_role_template(
    payload: GlobalRoleTemplateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> GlobalRoleTemplateResponse:
    try:
        template = await global_role_service.create_template(
            db, payload, admin, request
        )
    except BusinessRuleError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return GlobalRoleTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=GlobalRoleTemplateResponse)
async def update_global_role_template(
    template_id: int,
    payload: GlobalRoleTemplateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> GlobalRoleTemplateResponse:
    try:
        template = await global_role_service.update_template(
            db, template_id, payload, admin, request
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return GlobalRoleTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_role_template(
    template_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    try:
        await global_role_service.delete_template(db, template_id, admin, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
