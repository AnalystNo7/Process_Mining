from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.celery_app import celery_app
from app.db.models.users import User
from app.schemas.physical_datasets import TaskStatusResponse

router = APIRouter(prefix="/tasks", tags=["Задачи"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    _user: User = Depends(get_current_user),
) -> TaskStatusResponse:
    """Статус фоновой задачи Celery (для индикатора прогресса в UI)."""
    result = celery_app.AsyncResult(task_id)
    try:
        state = str(result.status)
        payload = TaskStatusResponse(task_id=task_id, status=state)
        if result.successful():
            payload.result = result.result
        elif result.failed():
            payload.error = str(result.result)
    except Exception:  # noqa: BLE001 — брокер недоступен → считаем статус неизвестным
        payload = TaskStatusResponse(task_id=task_id, status="UNKNOWN")
    return payload
