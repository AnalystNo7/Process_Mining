# T04: Локальная аутентификация (JWT)

## Цель
Реализовать логин/refresh/logout/me для локальных пользователей с JWT-токенами.

## Контекст
- `03_API.md` раздел "1. Аутентификация"
- `01_DATA_MODEL.md` таблицы `auth.users`, `auth.refresh_tokens`
- `05_INFRA.md` раздел "Безопасность"

## DoD
- [ ] `app/core/security.py`: функции `hash_password`, `verify_password` (через passlib bcrypt), `create_access_token`, `create_refresh_token`, `decode_token`.
- [ ] `app/api/v1/auth.py`: эндпоинты `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`.
- [ ] `app/services/auth_service.py`: бизнес-логика (проверка пароля, поиск пользователя, выдача токенов, ревокация).
- [ ] `app/api/deps.py`: dependency `get_current_user`, `require_admin`.
- [ ] CLI-команда `make create-admin` создаёт первого пользователя интерактивно (`python -m app.scripts.create_admin`).
- [ ] Audit log записывает события `user.login.success`, `user.login.failed`, `user.logout`.
- [ ] Все эндпоинты протестированы integration-тестами.

## Реализация

### `app/core/security.py`
```python
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
from jose import jwt, JWTError
from app.core.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

def create_access_token(subject: str | int, additional_claims: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(subject: str | int) -> tuple[str, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    token = jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire

def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
```

### `app/api/deps.py`
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token
from app.db.session import get_db
from app.db.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
    except (JWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid token")
    
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")
    return user
```

### `app/api/v1/auth.py`
Реализовать endpoints согласно `03_API.md`. При успешном логине — сохранять hash refresh-токена в `auth.refresh_tokens`. При logout — помечать `revoked_at`.

### CLI создания админа
`app/scripts/create_admin.py`:
```python
import asyncio
import getpass
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.users import User
from app.core.security import hash_password

async def main():
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.role == "admin"))
        if existing:
            print(f"Админ уже существует: {existing.username}")
            return
        username = input("Username: ")
        full_name = input("Full name: ")
        email = input("Email (optional): ").strip() or None
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("Пароли не совпадают")
            return
        user = User(username=username, full_name=full_name, email=email,
                    password_hash=hash_password(password), role="admin", is_active=True)
        db.add(user)
        await db.commit()
        print(f"Создан админ id={user.id}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Тесты
- `test_login_success` — корректные логин/пароль → 200 + токены.
- `test_login_wrong_password` → 401.
- `test_login_inactive_user` → 403.
- `test_refresh_success`.
- `test_refresh_revoked_token` → 401.
- `test_me_returns_current_user`.
- `test_logout_revokes_refresh_token`.

## Acceptance
После `make create-admin` можно сделать `POST /api/v1/auth/login` с этими credentials и получить access_token, который работает в `GET /api/v1/auth/me`.
