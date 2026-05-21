# T07: Audit log

## Цель
Запись всех значимых действий пользователей + админ-эндпоинт для просмотра.

## Контекст
- `01_DATA_MODEL.md` таблица `auth.audit_log`
- `03_API.md` раздел "15. Audit log"

## DoD
- [ ] Сервис `app/services/audit_service.py` с функцией `log_event(db, user, action, entity_type, entity_id, metadata, request)`.
- [ ] Middleware или dependency, прокидывающий IP и User-Agent в `audit_service`.
- [ ] Эндпоинт `GET /api/v1/admin/audit-log` с пагинацией и фильтрами.
- [ ] Все мутирующие действия (создание/изменение/удаление проектов, пользователей, датасетов, логин) вызывают `log_event`.
- [ ] UI-страница `/admin/audit-log` с таблицей и фильтрами.

## Реализация

### `app/services/audit_service.py`
```python
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from app.db.models.audit import AuditLog
from app.db.models.users import User

async def log_event(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
    request: Request | None = None,
) -> None:
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
        ip_address=ip,
        user_agent=ua,
    )
    db.add(entry)
    # commit делает вызывающий код (мы внутри транзакции)
```

### Стандартные actions (документировать)
```
user.login.success
user.login.failed
user.logout
user.create
user.update
user.deactivate
project.create
project.update
project.delete
physical_dataset.upload
physical_dataset.delete
virtual_dataset.create
virtual_dataset.delete
role_mapping.update
sla_rule.create / .update / .delete
dashboard.create / .update / .delete
slice.create / .update / .delete
annotation.create / .delete
```

### Эндпоинт
`GET /api/v1/admin/audit-log` с query params: `user_id`, `action` (LIKE), `entity_type`, `from`, `to`, `page`, `page_size`. JOIN с `auth.users` для имени.

### UI
Таблица AntD с колонками: Время, Пользователь, Действие, Сущность, ID, IP. Раскрытие строки → metadata JSON.

## Тесты
- `test_audit_log_records_login`.
- `test_audit_log_records_project_create`.
- `test_audit_log_filter_by_user`.
- `test_audit_log_admin_only_access`.

## Acceptance
После любого действия (логин, создание проекта) в `auth.audit_log` появляется запись. Админ видит её в UI на `/admin/audit-log`.
