import asyncio
from datetime import datetime, timezone

from fastapi import Request
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.db.models.users import RefreshToken, User
from app.services import audit_service, ldap_service


class AuthError(Exception):
    """Базовая ошибка аутентификации."""


class InvalidCredentialsError(AuthError):
    """Неверный логин или пароль."""


class UserInactiveError(AuthError):
    """Учётная запись заблокирована."""


class InvalidRefreshTokenError(AuthError):
    """Refresh-токен невалиден, просрочен или отозван."""


class LdapDisabledError(AuthError):
    """Попытка LDAP-входа при выключенной LDAP-интеграции."""


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    """Создаёт пару токенов и сохраняет hash refresh-токена в БД."""
    access_token = create_access_token(user.id, {"role": user.role})
    refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    return access_token, refresh_token


async def login(
    db: AsyncSession,
    username: str,
    password: str,
    use_ldap: bool = False,
    request: Request | None = None,
) -> tuple[User, str, str]:
    """Вход по логину/паролю. При use_ldap — аутентификация через LDAP/AD.
    Возвращает (user, access, refresh)."""
    if use_ldap:
        return await _login_ldap(db, username, password, request)

    user = await db.scalar(select(User).where(User.username == username))

    if user is None or user.password_hash is None or not verify_password(
        password, user.password_hash
    ):
        await audit_service.log_event(
            db, user, "user.login.failed", request=request, metadata={"username": username}
        )
        await db.commit()
        raise InvalidCredentialsError

    if not user.is_active:
        await audit_service.log_event(
            db,
            user,
            "user.login.failed",
            request=request,
            metadata={"username": username, "reason": "inactive"},
        )
        await db.commit()
        raise UserInactiveError

    access_token, refresh_token = await _issue_tokens(db, user)
    user.last_login_at = datetime.now(timezone.utc)
    await audit_service.log_event(db, user, "user.login.success", request=request)
    await db.commit()
    return user, access_token, refresh_token


async def _login_ldap(
    db: AsyncSession, username: str, password: str, request: Request | None
) -> tuple[User, str, str]:
    """Вход через LDAP/AD. При первом входе создаёт локального пользователя
    с is_ldap=True и ролью analyst."""
    if not settings.LDAP_ENABLED:
        raise LdapDisabledError

    ldap_info = await asyncio.to_thread(
        ldap_service.authenticate_ldap, username, password
    )
    if ldap_info is None:
        await audit_service.log_event(
            db,
            None,
            "user.login.failed",
            request=request,
            metadata={"username": username, "method": "ldap"},
        )
        await db.commit()
        raise InvalidCredentialsError

    user = await db.scalar(select(User).where(User.username == ldap_info.username))
    if user is None:
        user = User(
            username=ldap_info.username,
            full_name=ldap_info.full_name,
            email=ldap_info.email,
            password_hash=None,
            is_ldap=True,
            role="analyst",
            is_active=True,
        )
        db.add(user)
        await db.flush()

    if not user.is_active:
        await audit_service.log_event(
            db,
            user,
            "user.login.failed",
            request=request,
            metadata={"username": username, "method": "ldap", "reason": "inactive"},
        )
        await db.commit()
        raise UserInactiveError

    access_token, refresh_token = await _issue_tokens(db, user)
    user.last_login_at = datetime.now(timezone.utc)
    await audit_service.log_event(
        db, user, "user.login.success", request=request, metadata={"method": "ldap"}
    )
    await db.commit()
    return user, access_token, refresh_token


async def refresh(
    db: AsyncSession, refresh_token: str, request: Request | None = None
) -> tuple[User, str, str]:
    """Обновляет пару токенов (с ротацией refresh-токена)."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidRefreshTokenError
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise InvalidRefreshTokenError from exc

    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise InvalidRefreshTokenError

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError

    stored.revoked_at = now
    access_token, new_refresh_token = await _issue_tokens(db, user)
    await db.commit()
    return user, access_token, new_refresh_token


async def logout(
    db: AsyncSession, refresh_token: str, user: User, request: Request | None = None
) -> None:
    """Отзывает refresh-токен. Идемпотентно — неизвестный токен не вызывает ошибки."""
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
    await audit_service.log_event(db, user, "user.logout", request=request)
    await db.commit()
