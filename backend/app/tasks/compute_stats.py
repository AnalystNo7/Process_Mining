import asyncio
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.celery_app import celery_app
from app.db.models.datasets import VirtualDataset
from app.db.repositories.event_log import PostgresEventLogRepository
from app.db.session import AsyncTaskSessionLocal
from app.domain.mining.duration import compute_case_duration
from app.domain.mining.filters import apply_filter, parse_filters
from app.domain.mining.rework import compute_duration_comparison, compute_global_rework_pct
from app.domain.mining.role_mapping import apply_role_mapping
from app.domain.mining.variants import (
    compute_mean_occurrence_pct,
    compute_variability_pct,
    get_case_traces,
)


def _safe_float(value: Any) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def build_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Считает базовые KPI виртуального датасета (см. 01_DATA_MODEL.md)."""
    case_duration = compute_case_duration(df)
    comparison = compute_duration_comparison(df)
    has_rows = len(df) > 0
    return {
        "total_cases": int(df["case_id"].nunique()) if has_rows else 0,
        "total_events": int(len(df)),
        "unique_activities": int(df["activity"].nunique()) if has_rows else 0,
        "unique_resources": int(df["resource"].nunique()) if has_rows else 0,
        "unique_departments": int(df["department"].nunique()) if has_rows else 0,
        "period_start": (
            df["timestamp_start"].min().isoformat() if has_rows else None
        ),
        "period_end": df["timestamp_end"].max().isoformat() if has_rows else None,
        "avg_case_duration_seconds": _safe_float(
            case_duration["duration_seconds"].mean() if has_rows else None
        ),
        "avg_case_duration_with_rework_seconds": comparison[
            "avg_duration_with_rework_seconds"
        ],
        "avg_case_duration_without_rework_seconds": comparison[
            "avg_duration_without_rework_seconds"
        ],
        "cases_with_rework": comparison["n_cases_with_rework"],
        "cases_without_rework": comparison["n_cases_without_rework"],
        "global_rework_pct": compute_global_rework_pct(df),
        "unique_traces": int(get_case_traces(df).nunique()) if has_rows else 0,
        "variability_pct": compute_variability_pct(df),
        "mean_occurrence_pct": compute_mean_occurrence_pct(df),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


async def compute_and_store_stats(db: Any, vd_id: int) -> None:
    """Загружает событийный лог виртуального датасета, считает KPI и
    сохраняет их в virtual_datasets.cached_stats."""
    virtual = await db.get(VirtualDataset, vd_id)
    if virtual is None:
        return
    repo = PostgresEventLogRepository(db)
    df = await repo.load_to_dataframe(virtual.physical_dataset_id)
    df = apply_role_mapping(df, virtual.role_mapping_snapshot.get("mapping", {}))

    config_filters = virtual.config.get("filters")
    if config_filters:
        df = apply_filter(df, parse_filters(config_filters))

    virtual.cached_stats = build_stats(df)
    await db.commit()


async def _run(vd_id: int) -> None:
    async with AsyncTaskSessionLocal() as db:
        await compute_and_store_stats(db, vd_id)


@celery_app.task(name="compute_virtual_dataset_stats")  # type: ignore[untyped-decorator]
def compute_virtual_dataset_stats(vd_id: int) -> dict[str, int]:
    """Фоновый расчёт cached_stats виртуального датасета."""
    asyncio.run(_run(vd_id))
    return {"virtual_dataset_id": vd_id}
