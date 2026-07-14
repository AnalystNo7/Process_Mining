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
from app.db.models.projects import UploadTemplate
from app.db.models.users import AuditLog
from app.schemas.physical_datasets import SheetInfo
from app.services.physical_dataset_service import (
    _suggest_header_row,
    _suggest_sheet,
    process_upload,
    suggest_column_mapping,
)
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


def _xlsx_grid_bytes(grid: list[list]) -> bytes:
    """Лист «как есть», без строки заголовков от pandas."""
    buf = io.BytesIO()
    pd.DataFrame(grid).to_excel(buf, index=False, header=False)
    return buf.getvalue()


def _xlsx_multisheet_bytes(sheets: dict[str, list[dict]]) -> bytes:
    """Книга с несколькими листами (лист → строки-словари)."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()


# Файл с шапкой отчёта: настоящие заголовки на 3-й строке (index 2).
def _report_grid(n_rows: int = 3) -> list[list]:
    header = ["doc_id", "op", "t_start", "t_end"]
    data = [
        [f"D{i}", "Операция", datetime(2025, 1, 1 + i, 9, 0),
         datetime(2025, 1, 1 + i, 10, 0)]
        for i in range(n_rows)
    ]
    return [
        ["Отчёт за январь", None, None, None],
        [None, None, None, None],
        header,
        *data,
    ]


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
    db, project_id: int, uploaded_by: int, mapping: dict, header_row: int = 0
) -> PhysicalDataset:
    dataset = PhysicalDataset(
        project_id=project_id,
        name="DS",
        file_name="f.xlsx",
        file_size_bytes=1,
        file_hash="h",
        storage_path="",
        column_mapping=mapping,
        header_row=header_row,
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
    # Чистый файл: заголовки на первой строке, сырые строки — для пикера.
    assert data["header_row"] == 0
    assert data["raw_rows"][0] == ["doc_id", "op", "t_start", "t_end"]
    # Один лист — он же выбран.
    assert [s["name"] for s in data["sheets"]] == ["Sheet1"]
    assert data["sheet_name"] == "Sheet1"


def test_suggest_header_row_skips_report_header() -> None:
    raw_head = pd.DataFrame(_report_grid())
    assert _suggest_header_row(raw_head) == 2
    # Чистый файл — первая строка.
    assert _suggest_header_row(pd.DataFrame([["a", "b"], [1, 2]])) == 0


def test_suggest_sheet_picks_largest() -> None:
    infos = [
        SheetInfo(name="A", rows=3),
        SheetInfo(name="Общее", rows=50),
        SheetInfo(name="B", rows=10),
    ]
    assert _suggest_sheet(infos) == "Общее"
    # Один лист — он же.
    assert _suggest_sheet([SheetInfo(name="Solo", rows=5)]) == "Solo"
    # Все пустые — первый.
    assert _suggest_sheet(
        [SheetInfo(name="X", rows=0), SheetInfo(name="Y", rows=0)]
    ) == "X"


async def test_preview_suggests_largest_sheet(
    client, analyst_user, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    project_id = await _create_project(client, analyst_user.headers)
    content = _xlsx_multisheet_bytes(
        {"Малый": _small_rows(3), "Общее": _small_rows(20)}
    )
    resp = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", content, "application/vnd.ms-excel")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert {s["name"] for s in data["sheets"]} == {"Малый", "Общее"}
    assert data["sheet_name"] == "Общее"
    assert data["total_rows"] == 20


async def test_reparse_switches_sheet(
    client, analyst_user, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    project_id = await _create_project(client, analyst_user.headers)
    content = _xlsx_multisheet_bytes(
        {"Малый": _small_rows(3), "Общее": _small_rows(20)}
    )
    preview = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", content, "application/vnd.ms-excel")},
    )
    token = preview.json()["preview_token"]
    url = f"/api/v1/projects/{project_id}/physical-datasets/preview/reparse"

    resp = await client.post(
        url, headers=analyst_user.headers,
        json={"preview_token": token, "sheet_name": "Малый"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sheet_name"] == "Малый"
    assert data["total_rows"] == 3

    # Несуществующий лист → 400.
    resp = await client.post(
        url, headers=analyst_user.headers,
        json={"preview_token": token, "sheet_name": "Нет"},
    )
    assert resp.status_code == 400


async def test_preview_suggests_header_row_for_report_file(
    client, analyst_user, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", _xlsx_grid_bytes(_report_grid()),
                        "application/vnd.ms-excel")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["header_row"] == 2
    assert {c["name"] for c in data["columns"]} == {"doc_id", "op", "t_start", "t_end"}
    assert data["total_rows"] == 3
    assert data["raw_rows"][0][0] == "Отчёт за январь"


async def test_reparse_preview_changes_header_row(
    client, analyst_user, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    project_id = await _create_project(client, analyst_user.headers)
    preview = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", _xlsx_grid_bytes(_report_grid()),
                        "application/vnd.ms-excel")},
    )
    token = preview.json()["preview_token"]

    url = f"/api/v1/projects/{project_id}/physical-datasets/preview/reparse"
    resp = await client.post(
        url, headers=analyst_user.headers,
        json={"preview_token": token, "sheet_name": "Sheet1", "header_row": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["header_row"] == 0
    assert data["preview_token"] == token
    assert data["columns"][0]["name"] == "Отчёт за январь"

    # Строка за пределами файла → 400.
    resp = await client.post(
        url, headers=analyst_user.headers,
        json={"preview_token": token, "sheet_name": "Sheet1", "header_row": 999},
    )
    assert resp.status_code == 400

    # Неизвестный токен → 404.
    resp = await client.post(
        url, headers=analyst_user.headers,
        json={"preview_token": "0" * 32, "sheet_name": "Sheet1", "header_row": 0},
    )
    assert resp.status_code == 404


async def test_create_dataset_saves_header_row_and_template(
    client, analyst_user, db_session, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PATH", tmp_path)
    monkeypatch.setattr(
        upload_dataset_task, "delay", lambda dataset_id: SimpleNamespace(id="task-hr")
    )
    project_id = await _create_project(client, analyst_user.headers)
    preview = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets/preview",
        headers=analyst_user.headers,
        files={"file": ("log.xlsx", _xlsx_grid_bytes(_report_grid()),
                        "application/vnd.ms-excel")},
    )
    token = preview.json()["preview_token"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/physical-datasets",
        headers=analyst_user.headers,
        json={
            "name": "С шапкой",
            "preview_token": token,
            "column_mapping": _SMALL_MAPPING,
            "header_row": 2,
            "save_as_template": True,
        },
    )
    assert resp.status_code == 202
    dataset = await db_session.get(PhysicalDataset, resp.json()["id"])
    assert dataset.header_row == 2

    template = (
        await db_session.execute(
            select(UploadTemplate).where(UploadTemplate.project_id == project_id)
        )
    ).scalar_one()
    assert template.header_row == 2


async def test_process_upload_with_header_row(
    client, analyst_user, db_session, tmp_path
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _SMALL_MAPPING, header_row=2
    )
    path = tmp_path / "report.xlsx"
    path.write_bytes(_xlsx_grid_bytes(_report_grid(4)))

    await process_upload(db_session, dataset, path)
    assert dataset.status == "ready"
    assert dataset.total_events == 4


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


async def test_get_dataset_health(client, analyst_user, db_session, tmp_path) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    dataset = await _make_dataset(
        db_session, project_id, analyst_user.id, _SMALL_MAPPING
    )
    path = tmp_path / "health.xlsx"
    path.write_bytes(_xlsx_bytes(_small_rows(60)))
    await process_upload(db_session, dataset, path)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/physical-datasets/{dataset.id}/health",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"good", "warning", "poor"}
    assert len(data["checks"]) == 5


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
