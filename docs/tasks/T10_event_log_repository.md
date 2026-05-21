# T10: EventLogRepository

## Цель
Абстракция доступа к event log + PostgreSQL-реализация. Бизнес-логика не знает про SQL, работает через интерфейс.

## Контекст
- `01_DATA_MODEL.md` раздел "Принципы доступа к данным"
- `01_DATA_MODEL.md` таблица `events.event_log`

## DoD
- [ ] Protocol `EventLogRepository` в `app/domain/repository/event_log.py`.
- [ ] Реализация `PostgresEventLogRepository` в `app/db/repositories/event_log.py`.
- [ ] Методы: `bulk_insert`, `get_events_by_dataset` (с пагинацией / chunked iterator), `get_case_events`, `count_events`, `delete_by_dataset`, `get_unique_activities`, `get_unique_departments`, `get_unique_resources`, `load_to_dataframe` (для тяжёлых аналитических расчётов).
- [ ] Использует SQLAlchemy + asyncpg.
- [ ] `bulk_insert` использует `COPY` или batch INSERT по 10К строк (для производительности).
- [ ] DI-провайдер `get_event_log_repository` в FastAPI.
- [ ] Unit-тесты на каждый метод с реальной (test) БД.

## Реализация

### Protocol
```python
# app/domain/repository/event_log.py
from typing import Protocol, AsyncIterator
import pandas as pd
from app.domain.types import Event, EventFilter

class EventLogRepository(Protocol):
    async def bulk_insert(self, dataset_id: int, df: pd.DataFrame) -> int: ...
    async def delete_by_dataset(self, dataset_id: int) -> None: ...
    async def count_events(self, dataset_id: int, filters: EventFilter | None = None) -> int: ...
    async def get_case_events(self, dataset_id: int, case_id: str) -> list[Event]: ...
    async def get_unique_activities(self, dataset_id: int) -> list[str]: ...
    async def get_unique_departments(self, dataset_id: int) -> list[str]: ...
    async def get_unique_resources(self, dataset_id: int) -> list[str]: ...
    async def load_to_dataframe(self, dataset_id: int, filters: EventFilter | None = None) -> pd.DataFrame: ...
```

### Postgres-реализация
```python
class PostgresEventLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def bulk_insert(self, dataset_id: int, df: pd.DataFrame) -> int:
        # Подготовить данные
        records = []
        for _, row in df.iterrows():
            records.append({
                "physical_dataset_id": dataset_id,
                "case_id": row["case_id"],
                "activity": row["activity"],
                "timestamp_start": row["timestamp_start"],
                "timestamp_end": row["timestamp_end"],
                "resource": row.get("resource"),
                "department": row.get("department"),
                "attributes": row.get("attributes", {}),
            })
        
        BATCH = 5000
        n = 0
        for i in range(0, len(records), BATCH):
            chunk = records[i:i+BATCH]
            await self.session.execute(insert(EventLog), chunk)
            n += len(chunk)
        
        await self.session.commit()
        return n
    
    async def load_to_dataframe(self, dataset_id, filters=None) -> pd.DataFrame:
        # Загрузить через SQL → pandas
        query = "SELECT case_id, activity, timestamp_start, timestamp_end, resource, department, attributes FROM events.event_log WHERE physical_dataset_id = :ds_id"
        params = {"ds_id": dataset_id}
        if filters:
            # ... добавить WHERE-условия для каждого активного фильтра
            pass
        df = await asyncio.to_thread(
            pd.read_sql, query, self.session.bind.sync_engine.url, params=params
        )
        return df
```

### Применение фильтров
Здесь только базовые фильтры на event-уровне (date_range, activities, departments). Сложные фильтры (на уровне кейса — case_duration, with_rework) применяются уже в pandas в domain-логике после load_to_dataframe.

## Тесты
- `test_bulk_insert_5k_rows` → count_events возвращает 5000.
- `test_get_case_events_returns_sorted_by_time`.
- `test_get_unique_activities`.
- `test_filter_by_date_range`.
- `test_delete_by_dataset_removes_all`.

## Acceptance
Сценарий "вставили 25K строк → подсчёт работает за <1с → получение DataFrame работает" проходит.
