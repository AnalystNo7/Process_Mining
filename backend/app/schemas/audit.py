from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditUserBrief(BaseModel):
    id: int
    username: str


class AuditLogEntry(BaseModel):
    id: int
    user: AuditUserBrief | None
    action: str
    entity_type: str | None
    entity_id: int | None
    metadata: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
