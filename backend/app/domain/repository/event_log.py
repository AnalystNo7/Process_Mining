from collections.abc import AsyncIterator
from typing import Protocol

import pandas as pd

from app.domain.types import Event, EventFilter


class EventLogRepository(Protocol):
    """Абстракция доступа к журналу событий.

    Бизнес-логика работает только через этот интерфейс и не знает о СУБД.
    В MVP — единственная реализация PostgresEventLogRepository; архитектурно
    предусмотрена замена на ClickHouse без изменения доменного слоя."""

    async def bulk_insert(self, dataset_id: int, df: pd.DataFrame) -> int: ...

    async def delete_by_dataset(self, dataset_id: int) -> None: ...

    async def count_events(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> int: ...

    async def get_case_events(self, dataset_id: int, case_id: str) -> list[Event]: ...

    async def get_unique_activities(self, dataset_id: int) -> list[str]: ...

    async def get_unique_departments(self, dataset_id: int) -> list[str]: ...

    async def get_unique_resources(self, dataset_id: int) -> list[str]: ...

    def get_events_by_dataset(
        self, dataset_id: int, filters: EventFilter | None = None, chunk_size: int = 10000
    ) -> AsyncIterator[Event]: ...

    async def load_to_dataframe(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> pd.DataFrame: ...
