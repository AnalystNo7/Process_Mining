from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.audit import AuditLogEntry, AuditLogList, AuditUserBrief
from app.services import audit_service

router = APIRouter(prefix="/admin/audit-log", tags=["Аудит"])


@router.get("", response_model=AuditLogList)
async def list_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AuditLogList:
    rows, total = await audit_service.list_audit_log(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
    )
    items = [
        AuditLogEntry(
            id=log.id,
            user=AuditUserBrief(id=user.id, username=user.username)
            if user is not None
            else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            metadata=log.meta,
            # INET-колонка возвращается драйвером как объект ipaddress.* — приводим к str.
            ip_address=str(log.ip_address) if log.ip_address is not None else None,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log, user in rows
    ]
    return AuditLogList(items=items, total=total, page=page, page_size=page_size)
