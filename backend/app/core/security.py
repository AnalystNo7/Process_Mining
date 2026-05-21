import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хэш пароля."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет пароль против bcrypt-хэша."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_token(token: str) -> str:
    """SHA-256 refresh-токена — для хранения в БД (token_hash)."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(
    subject: str | int, additional_claims: dict[str, Any] | None = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "jti": uuid.uuid4().hex,
    }
    if additional_claims:
        payload.update(additional_claims)
    token: str = jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def create_refresh_token(subject: str | int) -> tuple[str, datetime]:
    """Возвращает (refresh_token, expires_at)."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
    }
    token: str = jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует и проверяет JWT. Бросает jose.JWTError при невалидном/просроченном."""
    payload: dict[str, Any] = jwt.decode(
        token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    return payload
