import io
from datetime import datetime, timedelta

import pandas as pd

from app.db.models.datasets import PhysicalDataset
from app.services.physical_dataset_service import process_upload

_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
    "resource": "user",
    "department": "dept",
}
_BASE = datetime(2025, 1, 1, 9, 0)


def _xlsx_with_rework(n_cases: int = 15) -> bytes:
    rows = []
    for case in range(n_cases):
        # Каждый кейс: Старт → Согласование → Согласование (повтор) → Конец.
        for i, activity in enumerate(["Старт", "Согласование", "Согласование", "Конец"]):
            rows.append(
                {
                    "doc_id": f"D{case}",
                    "op": activity,
                    "t_start": _BASE + timedelta(days=case, hours=i),
                    "t_end": _BASE + timedelta(days=case, hours=i, minutes=30),
                    "user": f"User{case % 4}",
                    "dept": "Отдел",
                }
            )
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


async def _setup_vd(client, headers, db, user_id: int, tmp_path) -> tuple[int, int]:
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
    path.write_bytes(_xlsx_with_rework())
    await process_upload(db, dataset, path)

    vd = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=headers,
        json={"name": "VD", "physical_dataset_id": dataset.id},
    )
    return project_id, int(vd.json()["id"])


async def test_rework_table(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/rework-table",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    soglasovanie = next(r for r in data["items"] if r["activity"] == "Согласование")
    assert soglasovanie["total"] == 30  # 2 на кейс × 15 кейсов
    assert soglasovanie["repeats"] == 15  # 1 повтор на кейс
    assert soglasovanie["rework_pct"] == 50.0
    assert data["global_rework_pct"] > 0


async def test_rework_table_unknown_vd(client, analyst_user) -> None:
    project = await client.post(
        "/api/v1/projects", headers=analyst_user.headers, json={"name": "P"}
    )
    project_id = project.json()["id"]
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/999999/analytics/rework-table",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 404


async def test_top_paths(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/top-paths",
        headers=analyst_user.headers,
        params={"n": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Все 15 кейсов имеют одинаковую трассу → 1 вариант покрывает все.
    assert data["total_cases"] == 15
    assert data["total_variants"] == 1
    assert data["variants"][0]["n_cases"] == 15
    assert data["variants"][0]["trace"] == ["Старт", "Согласование", "Согласование", "Конец"]


async def test_dfg(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/dfg",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    node_ids = {n["data"]["id"] for n in data["nodes"]}
    assert node_ids == {"Старт", "Согласование", "Конец"}
    edges = {(e["data"]["source"], e["data"]["target"]) for e in data["edges"]}
    assert ("Старт", "Согласование") in edges
    assert ("Согласование", "Согласование") in edges  # self-loop (повтор)
    assert data["start_activities"] == {"Старт": 15}


async def test_monthly_dynamics(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/monthly-dynamics",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert sum(row["n_events"] for row in items) == 60


async def test_bpmn_export(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/bpmn",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/bpmn+xml")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert "bpmn:definitions" in body
    assert "Согласование" in body  # узел из тестовых данных


async def test_process_map_top_paths(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/process-map",
        headers=analyst_user.headers,
        params={"mode": "top_paths", "n": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "top_paths"
    assert data["total_cases"] == 15
    assert data["total_variants"] == 1
    assert data["covered_cases"] == 15
    # Все кейсы имеют одну трассу → один путь покрывает всё.
    assert len(data["paths"]) == 1
    path = data["paths"][0]
    assert path["n_cases"] == 15
    assert path["trace"] == ["Старт", "Согласование", "Согласование", "Конец"]
    assert len(path["case_ids"]) == 15
    # Синтетические терминальные узлы.
    kinds = {n["data"]["id"]: n["data"]["kind"] for n in data["nodes"]}
    assert kinds["__start__"] == "start"
    assert kinds["__end__"] == "end"
    # Счётчик узла — вхождения операции: Согласование встречается 2 раза × 15.
    counts = {n["data"]["id"]: n["data"]["count"] for n in data["nodes"]}
    assert counts["Согласование"] == 30
    assert counts["Старт"] == 15


async def test_process_map_frequency(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/process-map",
        headers=analyst_user.headers,
        params={"mode": "frequency"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "frequency"
    assert data["paths"] == []
    node_ids = {n["data"]["id"] for n in data["nodes"]}
    assert node_ids == {"Старт", "Согласование", "Конец"}


async def test_operations(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/operations",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    items = {r["activity"]: r for r in resp.json()["items"]}
    assert items["Согласование"]["n_cases"] == 15
    assert items["Согласование"]["n_events"] == 30  # 2 вхождения × 15 кейсов
    assert items["Старт"]["n_events"] == 15
    assert 0 <= items["Согласование"]["avg_share_pct"] <= 100


async def test_filter_options(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/filter-options",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["departments"] == ["Отдел"]
    assert set(data["resources"]) == {"User0", "User1", "User2", "User3"}
    assert set(data["activities"]) == {"Старт", "Согласование", "Конец"}


async def test_resources(client, analyst_user, db_session, tmp_path) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/analytics/resources",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert {r["resource"] for r in items} == {"User0", "User1", "User2", "User3"}
