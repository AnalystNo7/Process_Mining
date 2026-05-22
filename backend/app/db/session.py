from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.APP_DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Отдельный движок для Celery-задач. Каждая задача выполняется в собственном
# event loop (asyncio.run), поэтому пул соединений переиспользовать нельзя —
# соединение от закрытого loop'а приводит к сбою на Windows (ProactorEventLoop).
# NullPool открывает соединение заново на текущем loop и закрывает после.
task_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=settings.APP_DEBUG,
)

AsyncTaskSessionLocal = async_sessionmaker(
    task_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: выдаёт async-сессию БД на время запроса."""
    async with AsyncSessionLocal() as session:
        yield session
