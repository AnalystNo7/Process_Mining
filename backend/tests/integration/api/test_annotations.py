import io
from datetime import datetime

import pandas as pd

from app.core.security import create_access_token, hash_password
from app.db.models.datasets import PhysicalDataset
from app.db.models.users import User
from app.services.physical_dataset_service import process_upload

_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
    "resource": "user",
    "department": "dept",
}


def _xlsx() -> bytes:
    rows = [
        {
            "doc_id": f"D{case}", "op": op,
            "t_start": datetime(2025, 1, 1 + case, 9, idx),
            "t_end": datetime(2025, 1, 1 + case, 10, idx),
            "user": "U", "dept": "Отдел",
        }
        for case in range(5)
        for idx, op in enumerate(["Старт", "Конец"])
    ]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


async def _setup_vd(client, headers, db, user_id: int, tmp_path) -> int:
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
    return int(vd.json()["id"])


async def _second_analyst(db) -> dict[str, str]:
    user = User(
        username="other", full_name="Пётр Петров", role="analyst", is_active=True,
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id, {"role": "analyst"})
    return {"Authorization": f"Bearer {token}"}


async def _create(client, headers, vd_id: int, **body) -> dict:
    resp = await client.post(
        f"/api/v1/virtual-datasets/{vd_id}/annotations", headers=headers, json=body
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_annotation_node(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    data = await _create(
        client, analyst_user.headers, vd_id,
        target_type="node", target={"activity": "Согласование"}, text="Узкое место",
    )
    assert data["target_type"] == "node"
    assert data["target"] == {"activity": "Согласование"}
    assert data["author_name"] == "Analyst"


async def test_create_annotation_edge(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    data = await _create(
        client, analyst_user.headers, vd_id,
        target_type="edge", target={"from": "Старт", "to": "Конец"}, text="Переход",
    )
    assert data["target"] == {"from": "Старт", "to": "Конец"}


async def test_create_annotation_case(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    data = await _create(
        client, analyst_user.headers, vd_id,
        target_type="case", target={"case_id": "D1"}, text="Аномальный кейс",
    )
    assert data["target"] == {"case_id": "D1"}


async def test_create_annotation_time_range(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    target = {"start_date": "2025-04-01", "end_date": "2025-04-30", "context": "operation:X"}
    data = await _create(
        client, analyst_user.headers, vd_id,
        target_type="time_range", target=target, text="Всплеск нагрузки",
    )
    assert data["target"] == target


async def test_create_annotation_invalid_target(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    resp = await client.post(
        f"/api/v1/virtual-datasets/{vd_id}/annotations",
        headers=analyst_user.headers,
        json={"target_type": "edge", "target": {"from": "Старт"}, "text": "?"},
    )
    assert resp.status_code == 422


async def test_list_annotations_filter_by_type(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    await _create(client, analyst_user.headers, vd_id,
                  target_type="node", target={"activity": "A"}, text="t1")
    await _create(client, analyst_user.headers, vd_id,
                  target_type="case", target={"case_id": "D0"}, text="t2")
    full = await client.get(
        f"/api/v1/virtual-datasets/{vd_id}/annotations", headers=analyst_user.headers
    )
    assert full.json()["total"] == 2
    only_nodes = await client.get(
        f"/api/v1/virtual-datasets/{vd_id}/annotations",
        headers=analyst_user.headers,
        params={"target_type": "node"},
    )
    assert only_nodes.json()["total"] == 1
    assert only_nodes.json()["items"][0]["target_type"] == "node"


async def test_other_analyst_sees_annotation_with_author(
    client, analyst_user, db_session, tmp_path
) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    await _create(client, analyst_user.headers, vd_id,
                  target_type="node", target={"activity": "A"}, text="Заметка А")
    other = await _second_analyst(db_session)
    resp = await client.get(
        f"/api/v1/virtual-datasets/{vd_id}/annotations", headers=other
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["author_name"] == "Analyst"


async def test_other_user_cannot_edit_annotation(
    client, analyst_user, db_session, tmp_path
) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    created = await _create(client, analyst_user.headers, vd_id,
                            target_type="node", target={"activity": "A"}, text="t")
    other = await _second_analyst(db_session)
    resp = await client.put(
        f"/api/v1/annotations/{created['id']}", headers=other, json={"text": "взлом"}
    )
    assert resp.status_code == 403


async def test_admin_can_edit_annotation(
    client, analyst_user, admin_user, db_session, tmp_path
) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    created = await _create(client, analyst_user.headers, vd_id,
                            target_type="node", target={"activity": "A"}, text="t")
    resp = await client.put(
        f"/api/v1/annotations/{created['id']}",
        headers=admin_user.headers,
        json={"text": "исправлено админом"},
    )
    assert resp.status_code == 200
    assert resp.json()["text"] == "исправлено админом"


async def test_delete_annotation(client, analyst_user, db_session, tmp_path) -> None:
    vd_id = await _setup_vd(client, analyst_user.headers, db_session, analyst_user.id, tmp_path)
    created = await _create(client, analyst_user.headers, vd_id,
                            target_type="case", target={"case_id": "D0"}, text="t")
    resp = await client.delete(
        f"/api/v1/annotations/{created['id']}", headers=analyst_user.headers
    )
    assert resp.status_code == 204
    listing = await client.get(
        f"/api/v1/virtual-datasets/{vd_id}/annotations", headers=analyst_user.headers
    )
    assert listing.json()["total"] == 0


async def test_annotations_unknown_vd(client, analyst_user) -> None:
    resp = await client.get(
        "/api/v1/virtual-datasets/999999/annotations", headers=analyst_user.headers
    )
    assert resp.status_code == 404
