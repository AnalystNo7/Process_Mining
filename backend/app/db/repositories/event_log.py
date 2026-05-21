from collections.abc import AsyncIterator
from typing import Any

import pandas as pd
from sqlalchemy import ColumnElement, delete, distinct, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event_log import EventLog
from app.domain.types import Event, EventFilter

_DF_COLUMNS = [
    "case_id",
    "activity",
    "timestamp_start",
    "timestamp_end",
    "resource",
    "department",
    "attributes",
    "own_duration_sec",
]
_INSERT_BATCH = 5000
_STREAM_CHUNK = 10000


def _na_to_none(value: Any) -> Any:
    """Приводит pandas-пропуски (NaN/NA) к Python None для драйвера БД."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


class PostgresEventLogRepository:
    """Реализация EventLogRepository поверх PostgreSQL (SQLAlchemy + asyncpg)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _conditions(
        dataset_id: int, filters: EventFilter | None
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [
            EventLog.physical_dataset_id == dataset_id
        ]
        if filters is None:
            return conditions
        if filters.date_range is not None:
            start, end = filters.date_range
            conditions.append(EventLog.timestamp_start >= start)
            conditions.append(EventLog.timestamp_start <= end)
        if filters.departments:
            conditions.append(EventLog.department.in_(filters.departments))
        if filters.resources:
            conditions.append(EventLog.resource.in_(filters.resources))
        if filters.activities:
            conditions.append(EventLog.activity.in_(filters.activities))
        if filters.case_ids:
            conditions.append(EventLog.case_id.in_(filters.case_ids))
        if filters.attributes_filter:
            for key, values in filters.attributes_filter.items():
                conditions.append(EventLog.attributes[key].astext.in_(values))
        return conditions

    @staticmethod
    def _to_event(row: EventLog) -> Event:
        return Event(
            case_id=row.case_id,
            activity=row.activity,
            timestamp_start=row.timestamp_start,
            timestamp_end=row.timestamp_end,
            resource=row.resource,
            department=row.department,
            attributes=row.attributes or {},
        )

    async def bulk_insert(self, dataset_id: int, df: pd.DataFrame) -> int:
        records = [
            {
                "physical_dataset_id": dataset_id,
                "case_id": str(row["case_id"]),
                "activity": str(row["activity"]),
                "timestamp_start": row["timestamp_start"],
                "timestamp_end": row["timestamp_end"],
                "resource": _na_to_none(row.get("resource")),
                "department": _na_to_none(row.get("department")),
                "attributes": row.get("attributes") or {},
            }
            for row in df.to_dict(orient="records")
        ]
        inserted = 0
        for i in range(0, len(records), _INSERT_BATCH):
            chunk = records[i : i + _INSERT_BATCH]
            if chunk:
                await self.session.execute(insert(EventLog), chunk)
                inserted += len(chunk)
        await self.session.commit()
        return inserted

    async def delete_by_dataset(self, dataset_id: int) -> None:
        await self.session.execute(
            delete(EventLog).where(EventLog.physical_dataset_id == dataset_id)
        )
        await self.session.commit()

    async def count_events(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(EventLog)
            .where(*self._conditions(dataset_id, filters))
        )
        return await self.session.scalar(stmt) or 0

    async def get_case_events(self, dataset_id: int, case_id: str) -> list[Event]:
        stmt = (
            select(EventLog)
            .where(EventLog.physical_dataset_id == dataset_id, EventLog.case_id == case_id)
            .order_by(EventLog.timestamp_start, EventLog.timestamp_end)
        )
        rows = (await self.session.scalars(stmt)).all()
        return [self._to_event(row) for row in rows]

    async def _unique_values(self, dataset_id: int, column: Any) -> list[str]:
        stmt = (
            select(distinct(column))
            .where(EventLog.physical_dataset_id == dataset_id, column.is_not(None))
            .order_by(column)
        )
        return [v for v in (await self.session.scalars(stmt)).all() if v is not None]

    async def get_unique_activities(self, dataset_id: int) -> list[str]:
        return await self._unique_values(dataset_id, EventLog.activity)

    async def get_unique_departments(self, dataset_id: int) -> list[str]:
        return await self._unique_values(dataset_id, EventLog.department)

    async def get_unique_resources(self, dataset_id: int) -> list[str]:
        return await self._unique_values(dataset_id, EventLog.resource)

    async def get_events_by_dataset(
        self, dataset_id: int, filters: EventFilter | None = None, chunk_size: int = _STREAM_CHUNK
    ) -> AsyncIterator[Event]:
        """Потоковая выборка событий порциями (для больших датасетов)."""
        conditions = self._conditions(dataset_id, filters)
        offset = 0
        while True:
            stmt = (
                select(EventLog)
                .where(*conditions)
                .order_by(EventLog.id)
                .limit(chunk_size)
                .offset(offset)
            )
            chunk = (await self.session.scalars(stmt)).all()
            if not chunk:
                break
            for row in chunk:
                yield self._to_event(row)
            offset += chunk_size

    async def load_to_dataframe(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> pd.DataFrame:
        """Загружает события датасета в pandas DataFrame для доменных расчётов."""
        stmt = select(
            EventLog.case_id,
            EventLog.activity,
            EventLog.timestamp_start,
            EventLog.timestamp_end,
            EventLog.resource,
            EventLog.department,
            EventLog.attributes,
            EventLog.own_duration_sec,
        ).where(*self._conditions(dataset_id, filters))
        rows = (await self.session.execute(stmt)).all()
        return pd.DataFrame(rows, columns=_DF_COLUMNS)
