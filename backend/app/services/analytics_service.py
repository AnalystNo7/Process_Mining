import pandas as pd

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.datasets import VirtualDataset
from app.db.repositories.event_log import PostgresEventLogRepository
from app.domain.mining.role_mapping import apply_role_mapping


async def load_vd_dataframe(
    db: AsyncSession, virtual: VirtualDataset
) -> pd.DataFrame:
    """Загружает событийный лог виртуального датасета и применяет маппинг
    ролей из его immutable-снимка. Возвращает DataFrame с колонками role и
    activity_with_role."""
    repo = PostgresEventLogRepository(db)
    df = await repo.load_to_dataframe(virtual.physical_dataset_id)
    mapping: dict[str, str] = virtual.role_mapping_snapshot.get("mapping", {})
    return apply_role_mapping(df, mapping)


def activity_column(activity_level: str) -> str:
    """Имя колонки операции по уровню детализации (raw — сырое, role — с ролями)."""
    return "activity_with_role" if activity_level == "role" else "activity"
