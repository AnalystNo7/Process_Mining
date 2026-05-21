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
    "resource": "user",
    "department": "dept",
}


def _xlsx_sla() -> bytes:
    """Понедельник 13.01.2025: одно событие 'A' на кейс.

    C1 длится 4 рабочих часа (нарушение SLA при пороге 2ч),
    C2 — 1 рабочий час (в пределах SLA)."""
    base = datetime(2025, 1, 13, 9, 0)
    rows = [
        {"doc_id": "C1", "op": "A", "t_start": base, "t_end": base.replace(hour=13),
         "user": "U1", "dept": "ЮУ"},
        {"doc_id": "C2", "op": "A", "t_start": base, "t_end": base.replace(hour=10),
         "user": "U2", "dept": "ЮУ"},
    ]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


async def _setup_vd_with_sla(client, headers, db, user_id: int, tmp_path) -> tuple[int, int]:
    """Проект + SLA-правило + физический и виртуальный датасеты.

    SLA-правило создаётся ДО виртуального датасета — он снимает immutable-снимок
    действующих правил при создании."""
    project = await client.post("/api/v1/projects", headers=headers, json={"name": "P"})
    project_id = int(project.json()["id"])

    await client.post(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers=headers,
        json={
            "role": "*",
            "operation_pattern": "*",
            "sla_value": 2,
            "sla_unit": "workhours",
            "tolerance_hours": 0,
            "target_compliance_pct": 90.0,
            "effective_from": "2020-01-01",
        },
    )

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
    path.write_bytes(_xlsx_sla())
    await process_upload(db, dataset, path)

    vd = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=headers,
        json={"name": "VD", "physical_dataset_id": dataset.id},
    )
    return project_id, int(vd.json()["id"])


async def test_sla_compliance_endpoint(
    client, analyst_user, db_session, tmp_path
) -> None:
    project_id, vd_id = await _setup_vd_with_sla(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}"
        "/analytics/sla-compliance",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    row = next(r for r in data["rows"] if r["activity"] == "A")
    assert row["total_events"] == 2
    assert row["events_with_sla"] == 2
    assert row["overdue_count"] == 1
    assert row["compliance_pct"] == 50.0
    assert data["overall_compliance_pct"] == 50.0


async def test_sla_compliance_no_rules(
    client, analyst_user, db_session, tmp_path
) -> None:
    """Без SLA-правил снимок пуст — операции есть, но без норматива."""
    project = await client.post(
        "/api/v1/projects", headers=analyst_user.headers, json={"name": "P"}
    )
    project_id = int(project.json()["id"])
    dataset = PhysicalDataset(
        project_id=project_id, name="DS", file_name="f.xlsx", file_size_bytes=1,
        file_hash="h", storage_path="", column_mapping=_MAPPING, total_events=0,
        total_cases=0, unique_activities=0, health_status="good", health_report={},
        uploaded_by=analyst_user.id, status="validating",
    )
    db_session.add(dataset)
    await db_session.commit()
    await db_session.refresh(dataset)
    path = tmp_path / "log.xlsx"
    path.write_bytes(_xlsx_sla())
    await process_upload(db_session, dataset, path)
    vd = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": dataset.id},
    )
    vd_id = int(vd.json()["id"])

    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}"
        "/analytics/sla-compliance",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    row = next(r for r in data["rows"] if r["activity"] == "A")
    assert row["events_with_sla"] == 0
    assert row["compliance_pct"] is None
    assert row["status"] == "no_rule"
    assert data["overall_compliance_pct"] is None


async def test_sla_compliance_table_widget(
    client, analyst_user, db_session, tmp_path
) -> None:
    project_id, vd_id = await _setup_vd_with_sla(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    dashboards = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
    )
    dashboard_id = dashboards.json()["items"][0]["id"]
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "sla_compliance_table", "title": "SLA", "config": {}},
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    data = resp.json()
    row = next(r for r in data["rows"] if r["activity"] == "A")
    assert row["overdue_count"] == 1
    assert row["compliance_pct"] == 50.0
    assert data["overall_compliance_pct"] == 50.0


async def test_sla_compliance_table_widget_filters_rows(
    client, analyst_user, db_session, tmp_path
) -> None:
    """show_only_operations_with_rules оставляет лишь операции с SLA."""
    project_id, vd_id = await _setup_vd_with_sla(
        client, analyst_user.headers, db_session, analyst_user.id, tmp_path
    )
    dashboards = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
    )
    dashboard_id = dashboards.json()["items"][0]["id"]
    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={
            "widget_type": "sla_compliance_table",
            "title": "SLA",
            "config": {"show_only_operations_with_rules": True},
        },
    )
    resp = await client.get(
        f"/api/v1/widgets/{widget.json()['id']}/data", headers=analyst_user.headers
    )
    assert resp.status_code == 200
    assert all(r["events_with_sla"] > 0 for r in resp.json()["rows"])
