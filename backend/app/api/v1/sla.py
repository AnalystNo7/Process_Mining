from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_project_owner_or_admin
from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.sla import SLARuleCreate, SLARuleList, SLARuleResponse, SLARuleUpdate
from app.services import sla_service

router = APIRouter(tags=["SLA-правила"])


@router.get("/projects/{project_id}/sla-rules", response_model=SLARuleList)
async def list_sla_rules(
    project_id: int,
    active_only: bool = False,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SLARuleList:
    items, total = await sla_service.list_rules(
        db, project_id, active_only=active_only, role=role
    )
    return SLARuleList(
        items=[SLARuleResponse.model_validate(r) for r in items], total=total
    )


@router.post(
    "/projects/{project_id}/sla-rules",
    response_model=SLARuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sla_rule(
    project_id: int,
    payload: SLARuleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _project: Project = Depends(require_project_owner_or_admin),
    user: User = Depends(get_current_user),
) -> SLARuleResponse:
    rule = await sla_service.create_rule(db, project_id, payload, user, request)
    return SLARuleResponse.model_validate(rule)


@router.patch("/sla-rules/{rule_id}", response_model=SLARuleResponse)
async def update_sla_rule(
    rule_id: int,
    payload: SLARuleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SLARuleResponse:
    try:
        rule = await sla_service.update_rule(db, rule_id, payload, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    return SLARuleResponse.model_validate(rule)


@router.delete("/sla-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sla_rule(
    rule_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        await sla_service.delete_rule(db, rule_id, user, request)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
