from fastapi import Request
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, EntityNotFoundError
from app.core.security import hash_password
from app.db.models.users import User
from app.schemas.users import UserCreate, UserUpdate
from app.services import audit_service


async def _count_active_admins(db: AsyncSession) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == "admin", User.is_active.is_(True))
    )
    return count or 0


async def _get_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise EntityNotFoundError(f"Пользователь с id={user_id} не найден")
    return user


async def list_users(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[User], int]:
    conditions: list[ColumnElement[bool]] = []
    if search:
        like = f"%{search}%"
        conditions.append(
            or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )
    if role is not None:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    count_stmt = select(func.count()).select_from(User)
    list_stmt = select(User)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        list_stmt = list_stmt.where(*conditions)

    total = await db.scalar(count_stmt) or 0
    list_stmt = list_stmt.order_by(User.id).limit(page_size).offset((page - 1) * page_size)
    items = list((await db.scalars(list_stmt)).all())
    return items, total


async def get_user(db: AsyncSession, user_id: int) -> User:
    return await _get_or_404(db, user_id)


async def create_user(
    db: AsyncSession, data: UserCreate, actor: User, request: Request | None = None
) -> User:
    if await db.scalar(select(User).where(User.username == data.username)) is not None:
        raise ConflictError(f"Пользователь с логином {data.username!r} уже существует")
    if data.email is not None and (
        await db.scalar(select(User).where(User.email == data.email)) is not None
    ):
        raise ConflictError(f"Пользователь с email {data.email!r} уже существует")
    if not data.is_ldap and not data.password:
        raise BusinessRuleError("Для локального пользователя обязателен пароль")

    user = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        role=data.role,
        is_ldap=data.is_ldap,
        password_hash=hash_password(data.password) if data.password else None,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await audit_service.log_event(
        db, actor, "user.create", "user", user.id, request=request,
        metadata={"username": user.username, "role": user.role},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user_id: int,
    data: UserUpdate,
    actor: User,
    request: Request | None = None,
) -> User:
    user = await _get_or_404(db, user_id)

    new_role = data.role if data.role is not None else user.role
    new_active = data.is_active if data.is_active is not None else user.is_active
    loses_admin = user.role == "admin" and user.is_active and (
        new_role != "admin" or not new_active
    )
    if loses_admin and await _count_active_admins(db) <= 1:
        raise BusinessRuleError(
            "Нельзя снять роль или деактивировать последнего администратора"
        )

    if data.email is not None and data.email != user.email:
        clash = await db.scalar(
            select(User).where(User.email == data.email, User.id != user_id)
        )
        if clash is not None:
            raise ConflictError(f"Пользователь с email {data.email!r} уже существует")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        user.password_hash = hash_password(data.password)

    await audit_service.log_event(
        db, actor, "user.update", "user", user.id, request=request
    )
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(
    db: AsyncSession, user_id: int, actor: User, request: Request | None = None
) -> None:
    """Мягкое удаление — установка is_active=False."""
    user = await _get_or_404(db, user_id)
    if user.role == "admin" and user.is_active and await _count_active_admins(db) <= 1:
        raise BusinessRuleError("Нельзя деактивировать последнего администратора")

    user.is_active = False
    await audit_service.log_event(
        db, actor, "user.deactivate", "user", user.id, request=request
    )
    await db.commit()
