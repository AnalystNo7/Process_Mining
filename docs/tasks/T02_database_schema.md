# T02: Схема БД и Alembic-миграции

## Цель

Создать все SQLAlchemy-модели для сущностей из `01_DATA_MODEL.md` и Alembic-миграцию, накатывающую полную схему БД.

## Контекст для чтения

- `01_DATA_MODEL.md` — весь файл (это первоисточник схемы)
- `05_INFRA.md` — раздел "Миграции БД"

## Definition of Done

- [ ] Созданы SQLAlchemy-модели для всех таблиц из `01_DATA_MODEL.md`:
  - `auth.users`, `auth.refresh_tokens`, `auth.audit_log`
  - `core.projects`, `core.physical_datasets`, `core.role_mappings`, `core.sla_rules`, `core.virtual_datasets`, `core.named_slices`, `core.dashboards`, `core.dashboard_widgets`, `core.annotations`, `core.upload_templates`, `core.global_role_templates`
  - `events.event_log`
- [ ] Используется async-friendly стиль SQLAlchemy 2.0 (mapped_column, DeclarativeBase).
- [ ] Базовый класс `Base` в `app/db/base.py`.
- [ ] Все модели в `app/db/models/` (по файлу на доменную область: `users.py`, `projects.py`, `datasets.py`, `dashboards.py`, `event_log.py`).
- [ ] Alembic настроен и связан с моделями (`env.py` импортирует `Base`).
- [ ] Создана начальная миграция `001_initial_schema.py`.
- [ ] `alembic upgrade head` накатывает миграцию без ошибок.
- [ ] `alembic downgrade base` откатывает её без ошибок.
- [ ] В БД появляются все 3 схемы и все таблицы с правильными индексами.

## Шаги реализации

1. **Создать `app/db/base.py`:**

```python
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

class Base(DeclarativeBase):
    pass
```

2. **Создать модели по файлам.** Для каждой таблицы из `01_DATA_MODEL.md` — соответствующий SQLAlchemy-класс. Пример:

```python
# app/db/models/users.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import INET, JSONB
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    is_ldap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'admin' | 'analyst'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="NOW()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="NOW()")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

Аналогично для всех остальных таблиц. **Важно:**
- Все `BIGSERIAL` → `mapped_column(BigInteger, primary_key=True)` (autoincrement по умолчанию).
- Все `TIMESTAMPTZ` → `DateTime(timezone=True)`.
- Все `JSONB` → `mapped_column(JSONB)`.
- Все CHECK-ограничения через `CheckConstraint` в `__table_args__`.
- Все индексы создать через `Index` в `__table_args__` или `index=True` на колонке.

3. **Создать `app/db/session.py`:**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

4. **Настроить Alembic.** Создать `backend/alembic.ini` и `backend/alembic/env.py`. В `env.py`:

```python
from app.core.config import settings
from app.db.base import Base
import app.db.models  # noqa: F401 — импорт ВСЕХ моделей

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))
target_metadata = Base.metadata
```

5. **Создать миграцию для схем.** Перед автогенерированной миграцией — добавить ручную для `CREATE SCHEMA`:

```python
def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS events")
    # ... далее автогенерированный код

def downgrade():
    # ... автогенерированный downgrade
    op.execute("DROP SCHEMA IF EXISTS events CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")
```

6. **Сгенерировать миграцию:**

```cmd
alembic revision --autogenerate -m "initial_schema"
```

Проверить результат — должны быть все таблицы со всеми колонками и индексами.

7. **Накатить:**

```cmd
alembic upgrade head
```

Проверить в pgAdmin — все таблицы созданы.

## Тесты

- `pytest tests/integration/test_migrations.py` — заглушка, проверяющая что `Base.metadata.tables` содержит все ожидаемые имена.

```python
# tests/integration/test_migrations.py
import app.db.models  # noqa
from app.db.base import Base

EXPECTED_TABLES = {
    "auth.users", "auth.refresh_tokens", "auth.audit_log",
    "core.projects", "core.physical_datasets", "core.role_mappings",
    "core.sla_rules", "core.virtual_datasets", "core.named_slices",
    "core.dashboards", "core.dashboard_widgets", "core.annotations",
    "core.upload_templates", "core.global_role_templates",
    "events.event_log",
}

def test_all_tables_registered():
    actual = {f"{t.schema}.{t.name}" for t in Base.metadata.tables.values()}
    assert EXPECTED_TABLES <= actual
```

## Acceptance criteria

`make migrate` отрабатывает с нуля на пустой БД и создаёт все таблицы с индексами. `\dt+ auth.*`, `\dt+ core.*`, `\dt+ events.*` в psql показывают полный список.
