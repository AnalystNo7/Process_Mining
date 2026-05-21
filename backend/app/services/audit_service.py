from datetime import datetime
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.users import AuditLog, User

# Стандартные значения action (для справки и единообразия по кодовой базе):
#   user.login.success / user.login.failed / user.logout
#   user.create / user.update / user.deactivate
#   project.create / project.update / project.delete
#   physical_dataset.upload / physical_dataset.delete
#   virtual_dataset.create / virtual_dataset.delete
#   role_mapping.update
#   sla_rule.create / sla_rule.update / sla_rule.delete
#   dashboard.create / dashboard.update / dashboard.delete
#   slice.create / slice.update / slice.delete
#   annotation.create / annotation.delete


async def log_event(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Добавляет запись в auth.audit_log. Commit выполняет вызывающий код.

    Примечание: колонка БД называется `metadata`, но в ORM-модели это атрибут
    `meta` (имя `metadata` зарезервировано в SQLAlchemy DeclarativeBase).
    """
    ip = request.client.host if request is not None and request.client is not None else None
    user_agent = request.headers.get("user-agent") if request is not None else None

    entry = AuditLog(
        user_id=user.id if user is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=metadata or {},
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(entry)


async def list_audit_log(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[tuple[AuditLog, User | None]], int]:
    """Возвращает записи журнала (с присоединённым пользователем) и общее число."""
    conditions = []
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if action:
        conditions.append(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if date_from is not None:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(AuditLog.created_at <= date_to)

    count_stmt = select(func.count()).select_from(AuditLog)
    list_stmt = select(AuditLog, User).outerjoin(User, AuditLog.user_id == User.id)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        list_stmt = list_stmt.where(*conditions)

    total = await db.scalar(count_stmt) or 0
    list_stmt = (
        list_stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = (await db.execute(list_stmt)).all()
    return [(row[0], row[1]) for row in rows], total
