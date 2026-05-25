import io
from datetime import datetime

import pandas as pd

from app.db.models.datasets import PhysicalDataset
from app.services.physical_dataset_service import process_upload
from app.services.widget_data_service import format_duration_seconds, format_value

_MAPPING = {
    "case_id": "doc_id",
    "activity": "op",
    "timestamp_start": "t_start",
    "timestamp_end": "t_end",
    "resource": "user",
    "department": "dept",
}


def test_format_value_number() -> None:
    assert format_value(1328, "number") == "1 328"


def test_format_value_percent() -> None:
    assert format_value(20.06, "percent") == "20,06%"


def test_format_value_duration() -> None:
    assert format_duration_seconds(2 * 86400 + 3 * 3600 + 5 * 60) == "2д 3ч 5м"


def test_format_value_none() -> None:
    assert format_value(None, "number") == "—"


def _xlsx() -> bytes:
    rows = []
    for case in range(15):
        for i, activity in enumerate(["Старт", "Согласование", "Согласование", "Конец"]):
            rows.append(
                {
                    "doc_id": f"D{case}",
                    "op": activity,
                    "t_start": datetime(2025, 1, 1 + case, 9, i),
                    "t_end": datetime(2025, 1, 1 + case, 10, i),
                    "user": f"User{case % 3}",
                    "dept": f"Отдел{case % 2}",
                }
            )
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


async def _setup(client, headers, db, user_id: int, tmp_path) -> tuple[int, list[dict]]:
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
    vd_id = int(vd.json()["id"])
    dashboards = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=headers,
    )
    dashboard_id = dashboards.json()["items"][0]["id"]
    detail = await client.get(f"/api/v1/dashboards/{dashboard_id}", headers=headers)
    return dashboard_id, detail.json()["widgets"]


async def test_kpi_card_widget_data(client, analyst_user, db_session, tmp_path) -> None:
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    kpi = next(
        w for w in widgets
        if w["widget_type"] == "kpi_card" and w["config"]["metric"] == "total_cases"
    )
    resp = await client.get(
        f"/api/v1/widgets/{kpi['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] == 15
    assert data["formatted"] == "15"


async def test_monthly_dynamics_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, _ = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "monthly_dynamics", "title": "Динамика", "config": {}},
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "line_data" in data
    assert sum(point["y"] for point in data["data"]) == 60


async def test_operations_dynamics_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = next(w for w in widgets if w["widget_type"] == "operations_dynamics")
    resp = await client.get(
        f"/api/v1/widgets/{widget['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert sum(p["y"] for p in data["bars"]) == 60  # 15 кейсов × 4 события
    assert data["line"][0]["y"] == 4.0  # ровно 4 операции на экземпляр


async def test_events_per_case_histogram_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = next(w for w in widgets if w["widget_type"] == "events_per_case_histogram")
    resp = await client.get(
        f"/api/v1/widgets/{widget['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"] == [{"x": 4, "y": 15}]


async def test_case_flow_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = next(w for w in widgets if w["widget_type"] == "case_flow_cumulative")
    resp = await client.get(
        f"/api/v1/widgets/{widget['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inflow"][-1]["y"] == 15  # все 15 кейсов накопительно
    assert data["outflow"][-1]["y"] == 15


async def test_operations_summary_short_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = next(w for w in widgets if w["widget_type"] == "operations_summary_short")
    resp = await client.get(
        f"/api/v1/widgets/{widget['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    rows = {r["activity"]: r for r in resp.json()["rows"]}
    assert rows["Согласование"]["pct_cases"] == 100.0
    assert rows["Согласование"]["rework_pct"] > 0


async def test_bar_chart_widget_data(client, analyst_user, db_session, tmp_path) -> None:
    dashboard_id, _ = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={
            "widget_type": "bar_chart",
            "title": "По подразделениям",
            "config": {"data_source": "top_departments"},
        },
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    assert {point["x"] for point in resp.json()["data"]} == {"Отдел0", "Отдел1"}


async def test_rework_table_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, _ = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "rework_table", "title": "Повторы", "config": {}},
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    soglasovanie = next(r for r in rows if r["activity"] == "Согласование")
    assert soglasovanie["repeats"] == 15


async def test_top_paths_graph_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, _ = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "top_paths_graph", "title": "Топ", "config": {"n_paths": 5}},
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    assert resp.json()["coverage"]["total_cases"] == 15


async def test_process_graph_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, _ = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "process_graph", "title": "Граф", "config": {}},
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    assert {n["data"]["id"] for n in resp.json()["nodes"]} == {
        "Старт", "Согласование", "Конец"
    }


async def test_unsupported_widget_returns_422(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, _ = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "unknown_widget_xyz", "title": "?", "config": {}},
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 422


async def test_widget_data_unknown_widget(client, analyst_user) -> None:
    resp = await client.get("/api/v1/widgets/999999/data", headers=analyst_user.headers)
    assert resp.status_code == 404
