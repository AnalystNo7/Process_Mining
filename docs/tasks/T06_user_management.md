# T06: Управление пользователями (admin-only)

## Цель
CRUD-эндпоинты для управления пользователями. Доступ — только админам.

## Контекст
- `03_API.md` раздел "2. Пользователи (/users)"
- `01_DATA_MODEL.md` таблица `auth.users`

## DoD
- [ ] Эндпоинты `GET /users`, `POST /users`, `GET /users/{id}`, `PATCH /users/{id}`, `DELETE /users/{id}` (soft delete).
- [ ] Все защищены `require_admin`.
- [ ] Pydantic-схемы `UserCreate`, `UserUpdate`, `UserResponse`, `UserList`.
- [ ] Сервис `user_service.py` с бизнес-логикой.
- [ ] Пагинация и фильтры по `search`, `role`, `is_active`.
- [ ] При смене пароля — `current_password` не требуется (это админ).
- [ ] Audit log на все мутирующие действия: `user.create`, `user.update`, `user.deactivate`.
- [ ] UI-страница `/admin/users` с таблицей и формами.

## Реализация

### Pydantic-схемы (`app/schemas/users.py`)
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str | None = None
    email: EmailStr | None = None
    role: Literal["admin", "analyst"]
    is_ldap: bool = False

class UserCreate(UserBase):
    password: str | None = Field(default=None, min_length=8)

class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: Literal["admin", "analyst"] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    
    model_config = {"from_attributes": True}

class UserList(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
```

### Эндпоинты
В `app/api/v1/users.py`. Используют `require_admin` dependency.

### UI
React-страница `/admin/users`:
- AntD `Table` с колонками: Username, ФИО, Email, Роль, LDAP, Активен, Создан, Последний вход.
- Кнопка `+ Создать` → модалка с формой.
- Action-кнопки: `✏️ Редактировать`, `🚫 Деактивировать` / `✓ Активировать`.
- Поиск + фильтры в шапке таблицы.

## Тесты
- `test_list_users_admin_can`, `test_list_users_analyst_cannot` (403).
- `test_create_user_validates_password_for_non_ldap`.
- `test_create_ldap_user_without_password`.
- `test_update_user_password`.
- `test_cannot_deactivate_last_admin` (защита от блокировки всех админов).

## Acceptance
В UI на `/admin/users` (под admin-логином) видна таблица пользователей, можно создать аналитика, заблокировать, поменять пароль.
