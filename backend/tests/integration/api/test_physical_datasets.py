import io
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import select

from app.celery_app import celery_app
from app.core.config import settings
from app.db.models.datasets import PhysicalDataset
from app.db.models.users import AuditLog
from app.services.physical_dataset_service import process_upload, suggest_column_mapping
from app.tasks.upload import upload_dataset_task

GOLDEN_DIR = Path(__file__).parents[4] / "golden_data"

_TESSA_MAPPING = {
    "case_id": "doc_id",
    "activity": "Операция",
    "timestamp_start": "in_progress_datetime",
    "timestamp_end": "completed_datetime",
    "resource": "task_user",
    "department": "task_user_department",
}

_SMALL_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
}


def _xlsx_bytes(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


def _small_rows(n: int = 60) -> list[dict]:
    return [
        {
            "doc_id": f"D{i % 12}",
            "op": f"Операция {i % 4}",
            "t_start": datetime(2025, 1, 1 + i % 20, 9, 0),
            "t_end": datetime(2025, 1, 1 + i % 20, 10, 0),
        }
        for i in range(n)
    ]


async def _create_project(client, headers) -> int:
    resp = await client.post(
        "/api/v1/projects", headers=headers, json={"name": "Договоры"}
    )
    return int(resp.json()["id"])


async def _make_dataset(
    db, project_id: int, uploaded_by: int, mapping: dict
) -> PhysicalDataset:
    dataset = PhysicalDataset(
        project_id=project_id,
        name="DS",
        file_name="f.xlsx",
        file_size_bytes=1,
        file_hash="h",
        storage_path="",
        column_mapping=mapping,
        total_events=0,
        total_cases=0,
        unique_activities=0,
        health_status="good",
        health_report={},
        uploaded_by=uploaded_by,
        status="validating",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


def test_suggest_column_mapping() -> None:
    mapping = suggest_column_mapping(
        ["doc_id", "Операция", "in_progress_datetime", "completed_datetime", "task_user"]
    )
    assert mapping["case_id"] == "doc_id"
    assert mapping["activity"] == "Операция"
    assert mapping["timestamp_start"] == "in_progress_datetime"


async def test_preview_returns_columns_and_token(
    client, analyst_user, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    project_id = await _create_project(client, analyst_user.headers)
    content = _xlsx_bytes(_small_rows(5))
    resp = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", content, "application/vnd.ms-excel")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 5
    assert data["preview_token"]
    assert {c["name"] for c in data["columns"]} == {"doc_id", "op", "t_start", "t_end"}


async def test_create_dataset_enqueues_task(
    client, analyst_user, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    monkeypatch.setattr(
        upload_dataset_task, "delay", lambda dataset_id: SimpleNamespace(id="task-xyz")
    )
    project_id = await _create_project(client, analyst_user.headers)
    preview = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", _xlsx_bytes(_small_rows(5)), "application/vnd.ms-excel")},
    )
    token = preview.json()["preview_token"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets",
        headers=analyst_user.headers,
        json={
            "name": "Выгрузка Q1",
            "preview_token": token,
            "column_mapping": _SMALL_MAPPING,
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "validating"
    assert data["task_id"] == "task-xyz"


async def test_process_upload_small(client, analyst_user, db_session, tmp_path) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _SMALL_MAPPING
    )
    path = tmp_path / "small.xlsx"
    path.write_bytes(_xlsx_bytes(_small_rows(60)))

    await process_upload(db_session, dataset, path)
    await db_session.refresh(dataset)
    assert dataset.status == "ready"
    assert dataset.total_events == 60
    assert dataset.total_cases == 12
    assert dataset.health_status in {"good", "warning", "poor"}
    assert dataset.health_report["checks"]


async def test_process_upload_validation_failure(
    client, analyst_user, db_session, tmp_path
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _SMALL_MAPPING
    )
    # timestamp_end раньше timestamp_start → ошибка валидации.
    bad = [
        {
            "doc_id": "D1",
            "op": "X",
            "t_start": datetime(2025, 1, 2),
            "t_end": datetime(2025, 1, 1),
        }
    ]
    path = tmp_path / "bad.xlsx"
    path.write_bytes(_xlsx_bytes(bad))

    await process_upload(db_session, dataset, path)
    await db_session.refresh(dataset)
    assert dataset.status == "failed"
    assert dataset.error_message


async def test_process_upload_synthetic_log(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _TESSA_MAPPING
    )
    await process_upload(db_session, dataset, GOLDEN_DIR / "synthetic_log.xlsx")
    await db_session.refresh(dataset)
    assert dataset.status == "ready"
    assert dataset.total_events == 25606
    assert dataset.total_cases == 1328
    assert dataset.unique_activities == 507


async def test_list_and_get_dataset(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _SMALL_MAPPING
    )
    list_resp = await client.get(
        f"/api/v1/projects/{project_id}/physical-datasets", headers=analyst_user.headers
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    get_resp = await client.get(
        f"/api/v1/projects/{project_id}/physical-datasets/{dataset.id}",
        headers=analyst_user.headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == dataset.id


async def test_delete_dataset(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _SMALL_MAPPING
    )
    dataset_id = dataset.id
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/physical-datasets/{dataset_id}",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 204
    db_session.expunge_all()
    assert await db_session.get(PhysicalDataset, dataset_id) is None

    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "physical_dataset.delete" in actions


async def test_get_task_status(
    client, analyst_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda task_id: SimpleNamespace(
            status="SUCCESS",
            successful=lambda: True,
            failed=lambda: False,
            result={"dataset_id": 1},
        ),
    )
    resp = await client.get("/api/v1/tasks/some-task-id", headers=analyst_user.headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
