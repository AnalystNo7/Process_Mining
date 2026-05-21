from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.db.models  # noqa: F401 — регистрирует модели в Base.metadata
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.models.users import User
from app.db.session import get_db
from app.main import app

# Отдельная тестовая БД. NullPool — чтобы соединения не переиспользовались
# между event-loop'ами разных тестов.
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/process_mining", "/process_mining_test")
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db() -> AsyncIterator[None]:
    """Перед каждым тестом: схемы + таблицы существуют, данные очищены."""
    async with test_engine.begin() as conn:
        for schema in ("auth", "core", "events"):
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        await conn.run_sync(Base.metadata.create_all)
        tables = ", ".join(
            f'"{t.schema}"."{t.name}"' for t in Base.metadata.sorted_tables
        )
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture(autouse=True)
def _mock_celery_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Заглушка постановки Celery-задач — тесты не обращаются к брокеру."""
    from app.tasks.compute_stats import compute_virtual_dataset_stats
    from app.tasks.upload import upload_dataset_task

    def _fake_delay(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(id="test-task-id")

    monkeypatch.setattr(upload_dataset_task, "delay", _fake_delay)
    monkeypatch.setattr(compute_virtual_dataset_stats, "delay", _fake_delay)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Прямой доступ к тестовой БД (создание фикстур-данных)."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP-клиент к приложению с подменой get_db на тестовую сессию."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@dataclass
class AuthedUser:
    """Созданный в БД пользователь с готовым access-токеном."""

    id: int
    username: str
    role: str
    token: str
    headers: dict[str, str]


async def _make_authed_user(session: AsyncSession, username: str, role: str) -> AuthedUser:
    user = User(
        username=username,
        full_name=username.capitalize(),
        email=f"{username}@example.com",
        password_hash=hash_password("password123"),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = create_access_token(user.id, {"role": role})
    return AuthedUser(
        id=user.id,
        username=username,
        role=role,
        token=token,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> AuthedUser:
    return await _make_authed_user(db_session, "admin", "admin")


@pytest_asyncio.fixture
async def analyst_user(db_session: AsyncSession) -> AuthedUser:
    return await _make_authed_user(db_session, "analyst", "analyst")
