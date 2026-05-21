from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.repositories.event_log import PostgresEventLogRepository
from app.db.session import get_db
from app.domain.repository.event_log import EventLogRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Извлекает текущего пользователя из access-токена."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise credentials_error from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или заблокирован",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Допускает только пользователей с ролью admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Требуется роль администратора"
        )
    return user


async def require_project_owner_or_admin(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Допускает создателя проекта или администратора. Возвращает проект."""
    project = await db.get(Project, project_id)
    if project is None or project.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден")
    if user.role != "admin" and project.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для владельца проекта или администратора",
        )
    return project


def get_event_log_repository(
    db: AsyncSession = Depends(get_db),
) -> EventLogRepository:
    """DI-провайдер репозитория журнала событий."""
    return PostgresEventLogRepository(db)
