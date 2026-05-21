from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.users import AuditLog, User


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

    Расширяется в задаче T07 (просмотр журнала, полный перечень действий).
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
