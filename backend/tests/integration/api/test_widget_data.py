import io
from datetime import datetime

import pandas as pd

from app.db.models.datasets import PhysicalDataset
from app.services.physical_dataset_service import process_upload
from app.services.widget_data_service import (
    _pick_duration_unit,
    format_duration_seconds,
    format_value,
)

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
    # Адаптивно: до 2 старших единиц, с секундами для коротких.
    assert format_duration_seconds(2 * 86400 + 3 * 3600 + 5 * 60) == "2д 3ч"
    assert format_duration_seconds(45) == "45с"
    assert format_duration_seconds(90) == "1м 30с"
    assert format_duration_seconds(3725) == "1ч 2м"
    assert format_duration_seconds(0) == "0с"
    assert format_duration_seconds(3 * 86400) == "3д"


def test_format_value_none() -> None:
    assert format_value(None, "number") == "—"


def test_pick_duration_unit() -> None:
    assert _pick_duration_unit(89) == ("секунды", 1.0)
    assert _pick_duration_unit(100) == ("минуты", 60.0)
    assert _pick_duration_unit(2 * 3600) == ("часы", 3600.0)
    assert _pick_duration_unit(3 * 86400) == ("дни", 86400.0)


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
    # Линия длительности: подписана только единицей, hover — по точкам.
    assert data["line_unit"]
    assert data["line_label"] == data["line_unit"]
    assert len(data["line_text"]) == len(data["data"])


async def test_monthly_dynamics_respects_granularity(
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
    wid = widget.json()["id"]

    # По умолчанию (месяц): все события января 2025 — один бакет.
    resp = await client.get(
        f"/api/v1/widgets/{wid}/data", headers=analyst_user.headers
    )
    assert len(resp.json()["data"]) == 1

    # Переключаем гранулярность дашборда на «день» → 15 суточных бакетов.
    patched = await client.patch(
        f"/api/v1/dashboards/{dashboard_id}",
        headers=analyst_user.headers,
        json={"global_filters": {"granularity": "D"}},
    )
    assert patched.status_code == 200
    resp = await client.get(
        f"/api/v1/widgets/{wid}/data", headers=analyst_user.headers
    )
    data = resp.json()
    assert len(data["data"]) == 15
    assert sum(point["y"] for point in data["data"]) == 60


async def test_operations_dynamics_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    dashboard_id, _widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    # T47: виджет operations_dynamics больше не входит в дефолтный набор,
    # создаём его явно для проверки эндпоинта данных.
    created = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "operations_dynamics", "title": "Динамика",
              "config": {}, "tab": "process.duration"},
    )
    assert created.status_code == 201
    widget = created.json()
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


async def test_operation_durations_boxplot_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    """T45: дефолтный виджет на process.duration отдаёт распределение
    длительностей по операциям. На синтетических данных _xlsx() — 3 уникальные
    операции (Старт/Согласование/Конец), все события длиной по 1 часу."""
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    boxplot = next(
        w for w in widgets
        if w["widget_type"] == "operation_durations_boxplot"
    )
    resp = await client.get(
        f"/api/v1/widgets/{boxplot['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    names = {t["name"] for t in data["traces"]}
    assert names == {"Старт", "Согласование", "Конец"}
    for trace in data["traces"]:
        # _xlsx() — все события по 1 часу → 3600 сек.
        assert trace["median"] == 3600.0
        assert trace["mean"] == 3600.0
        assert trace["min"] == trace["max"] == 3600.0
        assert trace["y"], "y не должно быть пустым"


async def test_widget_data_query_param_overrides_limit(
    client, analyst_user, db_session, tmp_path
) -> None:
    """Временный override через query-параметры: ?limit=2&sort_by=duration
    ограничивает выдачу боксплота двумя операциями (config в БД не меняется)."""
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    boxplot = next(
        w for w in widgets if w["widget_type"] == "operation_durations_boxplot"
    )
    resp = await client.get(
        f"/api/v1/widgets/{boxplot['id']}/data",
        params={"limit": 2, "sort_by": "duration"},
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["traces"]) == 2


async def test_case_duration_cdf_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    """Комбо: дефолтный CDF на process.duration отдаёт точки кривой и % в SLA."""
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    cdf = next(w for w in widgets if w["widget_type"] == "case_duration_cdf")
    resp = await client.get(
        f"/api/v1/widgets/{cdf['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["points"], "points не должны быть пустыми"
    assert data["points"][-1]["y"] == 100.0
    # _xlsx(): кейс длится с 9:i по 10:i — около часа; цель SLA 24ч → 100%.
    assert data["sla_target_seconds"] == 24 * 3600
    assert data["pct_within_sla"] == 100.0


async def test_case_duration_cdf_sla_editable(
    client, analyst_user, db_session, tmp_path
) -> None:
    """Ручное изменение SLA в config виджета меняет линию SLA на графике CDF."""
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    cdf = next(w for w in widgets if w["widget_type"] == "case_duration_cdf")
    patch = await client.patch(
        f"/api/v1/widgets/{cdf['id']}",
        json={"config": {"sla_target_hours": 48}},
        headers=analyst_user.headers,
    )
    assert patch.status_code == 200
    resp = await client.get(
        f"/api/v1/widgets/{cdf['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    assert resp.json()["sla_target_seconds"] == 48 * 3600


async def test_duration_bottleneck_heatmap_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    heatmap = next(
        w for w in widgets if w["widget_type"] == "duration_bottleneck_heatmap"
    )
    resp = await client.get(
        f"/api/v1/widgets/{heatmap['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cells"], "cells не должны быть пустыми"
    # Операции теперь по оси Y (y_categories), разрез — по X.
    assert set(data["y_categories"]) <= {"Старт", "Согласование", "Конец"}
    assert data["x_label"] == "Департамент"
    assert data["y_label"] == "Операция"


async def test_sojourn_vs_own_widget_data(
    client, analyst_user, db_session, tmp_path
) -> None:
    _, widgets = await _setup(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    sojourn = next(w for w in widgets if w["widget_type"] == "sojourn_vs_own")
    resp = await client.get(
        f"/api/v1/widgets/{sojourn['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rows"], "rows не должны быть пустыми"
    first = data["rows"][0]
    assert {"activity", "work_seconds", "wait_seconds", "n"} <= set(first)


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
