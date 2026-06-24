import io
from datetime import datetime

import pandas as pd

from app.db.models.datasets import PhysicalDataset
from app.services.physical_dataset_service import process_upload

_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
}


def _xlsx() -> bytes:
    rows = []
    for case in range(10):
        # Кейс с повтором операции "Согласование".
        for i, activity in enumerate(["Старт", "Согласование", "Согласование", "Конец"]):
            rows.append(
                {
                    "doc_id": f"DOC-{case}",
                    "op": activity,
                    "t_start": datetime(2025, 1, 1 + case, 9, i),
                    "t_end": datetime(2025, 1, 1 + case, 10, i),
                }
            )
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


async def _setup(client, headers, db, user_id: int, tmp_path) -> tuple[int, int]:
    project = await client.post("/api/v1/projects", headers=headers, json={"name": "P"})
    project_id = int(project.json()["id"])
    dataset = PhysicalDataset(
        project_id=project_id, name="DS", file_name="f.xlsx", file_size_bytes=1,
        file_hash="h", storage_path="", column_mapping=_MAPPING, total_events=0,
        total_cases=0, unique_activities=0, health_status="good", health_report={},
        uploaded_by=user_id, status="validating",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    path = tmp_path / "log.xlsx"
    path.write_bytes(_xlsx())
    await process_upload(db, dataset, path)
    vd = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=headers,
        json={"name": "VD", "physical_dataset_id": dataset.id},
    )
    return project_id, int(vd.json()["id"])


async def test_list_cases(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/cases",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert all(case["has_rework"] for case in data["items"])


async def test_list_cases_pagination(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/cases",
        headers=analyst_user.headers,
        params={"page": 1, "page_size": 3},
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3
    assert resp.json()["total"] == 10


async def test_case_detail(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/case/DOC-3",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "DOC-3"
    assert data["n_events"] == 4
    assert data["has_rework"] is True
    # Второе "Согласование" помечено как повтор.
    repeats = [e for e in data["events"] if e["is_repeat"]]
    assert any(e["activity"] == "Согласование" for e in repeats)


async def test_case_detail_not_found(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/case/NOPE",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 404


async def test_list_events(client, analyst_user, db_session, tmp_path) -> None:
    """T44: эндпоинт /events отдаёт сырые события постранично."""
    project_id, vd_id = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/events",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # 10 кейсов × 4 события = 40 событий.
    assert data["total"] == 40
    assert len(data["items"]) == 40
    first = data["items"][0]
    assert {"case_id", "activity", "timestamp_start", "timestamp_end",
            "resource", "department", "own_duration_seconds"} <= set(first)


async def test_list_events_pagination(
    client, analyst_user, db_session, tmp_path
) -> None:
    project_id, vd_id = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/events",
        headers=analyst_user.headers,
        params={"page": 2, "page_size": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 10
    assert data["total"] == 40
    assert data["page"] == 2
