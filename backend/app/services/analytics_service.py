import json

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.datasets import VirtualDataset
from app.db.repositories.event_log import PostgresEventLogRepository
from app.domain.mining.filters import apply_filter, parse_filters
from app.domain.mining.role_mapping import apply_role_mapping
from app.domain.types import EventFilter


def filter_from_query(filters_json: str | None) -> EventFilter | None:
    """Разбирает query-параметр filters (JSON) в EventFilter."""
    if not filters_json:
        return None
    return parse_filters(json.loads(filters_json))


async def load_vd_dataframe(
    db: AsyncSession,
    virtual: VirtualDataset,
    event_filter: EventFilter | None = None,
) -> pd.DataFrame:
    """Загружает событийный лог виртуального датасета, применяет маппинг
    ролей из его immutable-снимка и (опционально) фильтр."""
    repo = PostgresEventLogRepository(db)
    df = await repo.load_to_dataframe(virtual.physical_dataset_id)
    df = apply_role_mapping(df, virtual.role_mapping_snapshot.get("mapping", {}))
    if event_filter is not None:
        df = apply_filter(df, event_filter)
    return df


def activity_column(activity_level: str) -> str:
    """Имя колонки операции по уровню детализации (raw — сырое, role — с ролями)."""
    return "activity_with_role" if activity_level == "role" else "activity"
