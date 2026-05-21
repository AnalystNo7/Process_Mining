from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.db.models  # noqa: F401 — регистрирует модели в Base.metadata
from app.core.config import settings
from app.db.base import Base
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
