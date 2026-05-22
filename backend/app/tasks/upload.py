import asyncio
from pathlib import Path
from typing import Any

from app.celery_app import celery_app
from app.db.models.datasets import PhysicalDataset
from app.db.session import AsyncTaskSessionLocal
from app.services import physical_dataset_service


async def _run_upload(dataset_id: int) -> None:
    async with AsyncTaskSessionLocal() as db:
        dataset = await db.get(PhysicalDataset, dataset_id)
        if dataset is None:
            return
        await physical_dataset_service.process_upload(
            db, dataset, Path(dataset.storage_path)
        )


@celery_app.task(name="upload_dataset")  # type: ignore[untyped-decorator]
def upload_dataset_task(dataset_id: int) -> dict[str, Any]:
    """Фоновая обработка загруженного физ.датасета."""
    asyncio.run(_run_upload(dataset_id))
    return {"dataset_id": dataset_id}
