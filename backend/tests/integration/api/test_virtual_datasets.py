import io
from datetime import datetime

import pandas as pd
from sqlalchemy import select

from app.db.models.datasets import PhysicalDataset, VirtualDataset
from app.services.physical_dataset_service import process_upload

_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
    "department": "dept",
}


def _xlsx_with_departments(n: int = 60) -> bytes:
    rows = [
        {
            "doc_id": f"D{i % 10}",
            "op": f"Согласование Отдел {i % 3}",
            "t_start": datetime(2025, 1, 1 + i % 20, 9, 0),
            "t_end": datetime(2025, 1, 1 + i % 20, 10, 0),
            "dept": f"Отдел {i % 3}",
        }
        for i in range(n)
    ]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


async def _create_project(client, headers) -> int:
    resp = await client.post("/api/v1/projects", headers=headers, json={"name": "Проект"})
    return int(resp.json()["id"])


async def _make_physical(db, project_id: int, uploaded_by: int) -> PhysicalDataset:
    dataset = PhysicalDataset(
        project_id=project_id,
        name="DS",
        file_name="f.xlsx",
        file_size_bytes=1,
        file_hash="h",
        storage_path="",
        column_mapping=_MAPPING,
        total_events=0,
        total_cases=0,
        unique_activities=0,
        health_status="good",
        health_report={},
        uploaded_by=uploaded_by,
        status="ready",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def test_create_vd_snapshots_role_mapping(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _make_physical(db_session, project_id, analyst_user.id)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD-1", "physical_dataset_id": physical.id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role_mapping_snapshot"]["version"] == 1
    assert data["sla_rules_snapshot"] == []
    assert data["cached_stats"] is None


async def test_update_role_mapping_does_not_affect_existing_vd(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _make_physical(db_session, project_id, analyst_user.id)
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD-1", "physical_dataset_id": physical.id},
    )
    vd_id = created.json()["id"]

    # Меняем маппинг ролей проекта (создаётся версия 2).
    await client.put(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
        json={"mapping": {"X": "Инициатор"}, "roles": ["Инициатор"]},
    )

    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}",
        headers=analyst_user.headers,
    )
    # Снимок виртуального датасета остался на версии 1 (immutable).
    assert resp.json()["role_mapping_snapshot"]["version"] == 1


async def test_create_vd_unknown_physical_dataset(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": 999999},
    )
    assert resp.status_code == 404


async def test_list_virtual_datasets(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _make_physical(db_session, project_id, analyst_user.id)
    for i in range(2):
        await client.post(
            f"/api/v1/projects/{project_id}/virtual-datasets",
            headers=analyst_user.headers,
            json={"name": f"VD-{i}", "physical_dataset_id": physical.id},
        )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_delete_vd_only_owner(client, analyst_user, admin_user, db_session) -> None:
    project_id = await _create_project(client, admin_user.headers)
    physical = await _make_physical(db_session, project_id, admin_user.id)
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=admin_user.headers,
        json={"name": "VD", "physical_dataset_id": physical.id},
    )
    vd_id = created.json()["id"]

    # Аналитик (не владелец) — отказ.
    forbidden = await client.delete(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}",
        headers=analyst_user.headers,
    )
    assert forbidden.status_code == 403

    # Владелец-админ — успех.
    ok = await client.delete(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}",
        headers=admin_user.headers,
    )
    assert ok.status_code == 204
    db_session.expunge_all()
    assert await db_session.get(VirtualDataset, vd_id) is None


async def test_role_breakdown(client, analyst_user, db_session, tmp_path) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _make_physical(db_session, project_id, analyst_user.id)
    path = tmp_path / "log.xlsx"
    path.write_bytes(_xlsx_with_departments(60))
    await process_upload(db_session, physical, path)

    # Размечаем подразделения по ролям.
    await client.put(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
        json={
            "mapping": {
                "Отдел 0": "Инициатор",
                "Отдел 1": "Инициатор",
                "Отдел 2": "Юридическое управление",
            },
            "roles": ["Инициатор", "Юридическое управление"],
        },
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": physical.id},
    )
    vd_id = created.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/role-breakdown",
        headers=analyst_user.headers,
        params={"role": "Инициатор"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert {d["name"] for d in data["departments"]} == {"Отдел 0", "Отдел 1"}
    assert data["total_events"] == 40


async def test_activity_breakdown(client, analyst_user, db_session, tmp_path) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _make_physical(db_session, project_id, analyst_user.id)
    path = tmp_path / "log.xlsx"
    path.write_bytes(_xlsx_with_departments(60))
    await process_upload(db_session, physical, path)

    await client.put(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
        json={
            "mapping": {"Отдел 0": "Инициатор", "Отдел 1": "Инициатор", "Отдел 2": "Инициатор"},
            "roles": ["Инициатор"],
        },
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": physical.id},
    )
    vd_id = created.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/activity-breakdown",
        headers=analyst_user.headers,
        params={"activity_with_role": "Согласование Инициатор"},
    )
    assert resp.status_code == 200
    operations = {op["name"] for op in resp.json()["operations"]}
    assert operations == {"Согласование Отдел 0", "Согласование Отдел 1", "Согласование Отдел 2"}


async def test_audit_log_on_vd_create(client, analyst_user, db_session) -> None:
    from app.db.models.users import AuditLog

    project_id = await _create_project(client, analyst_user.headers)
    physical = await _make_physical(db_session, project_id, analyst_user.id)
    await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": physical.id},
    )
    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "virtual_dataset.create" in actions
