import io
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.db.models.datasets import PhysicalDataset
from app.services.physical_dataset_service import process_upload
from app.tasks.compute_stats import build_stats, compute_and_store_stats

GOLDEN_DIR = Path(__file__).parents[3] / "golden_data"

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


def test_build_stats_structure() -> None:
    base = datetime(2025, 1, 1, tzinfo=__import__("datetime").timezone.utc)
    df = pd.DataFrame(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": base,
             "timestamp_end": base + timedelta(hours=1), "resource": "U1",
             "department": "D1"},
            {"case_id": "C1", "activity": "A", "timestamp_start": base,
             "timestamp_end": base + timedelta(hours=2), "resource": "U1",
             "department": "D1"},
            {"case_id": "C2", "activity": "A", "timestamp_start": base,
             "timestamp_end": base + timedelta(hours=1), "resource": "U2",
             "department": "D2"},
        ]
    )
    stats = build_stats(df)
    assert stats["total_cases"] == 2
    assert stats["total_events"] == 3
    assert stats["cases_with_rework"] == 1
    assert stats["computed_at"]


async def _create_project(client, headers) -> int:
    resp = await client.post("/api/v1/projects", headers=headers, json={"name": "P"})
    return int(resp.json()["id"])


async def _physical(db, project_id: int, user_id: int, mapping: dict) -> PhysicalDataset:
    dataset = PhysicalDataset(
        project_id=project_id, name="DS", file_name="f.xlsx", file_size_bytes=1,
        file_hash="h", storage_path="", column_mapping=mapping, total_events=0,
        total_cases=0, unique_activities=0, health_status="good", health_report={},
        uploaded_by=user_id, status="validating",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def test_compute_stats_small(client, analyst_user, db_session, tmp_path) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _physical(db_session, project_id, analyst_user.id, _SMALL_MAPPING)

    rows = [
        {
            "doc_id": f"D{i % 12}",
            "op": f"Операция {i % 4}",
            "t_start": datetime(2025, 1, 1 + i % 20, 9, 0),
            "t_end": datetime(2025, 1, 1 + i % 20, 10, 0),
        }
        for i in range(60)
    ]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    path = tmp_path / "log.xlsx"
    path.write_bytes(buf.getvalue())
    await process_upload(db_session, physical, path)

    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": physical.id},
    )
    vd_id = int(created.json()["id"])

    await compute_and_store_stats(db_session, vd_id)

    detail = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}",
        headers=analyst_user.headers,
    )
    stats = detail.json()["cached_stats"]
    assert stats is not None
    assert stats["total_events"] == 60
    assert stats["total_cases"] == 12


async def test_compute_stats_matches_golden(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical = await _physical(db_session, project_id, analyst_user.id, _TESSA_MAPPING)
    await process_upload(db_session, physical, GOLDEN_DIR / "synthetic_log.xlsx")

    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=analyst_user.headers,
        json={"name": "VD", "physical_dataset_id": physical.id},
    )
    vd_id = int(created.json()["id"])

    await compute_and_store_stats(db_session, vd_id)
    detail = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}",
        headers=analyst_user.headers,
    )
    stats = detail.json()["cached_stats"]
    assert stats["total_cases"] == 1328
    assert stats["total_events"] == 25606
    assert stats["unique_activities"] == 507
    assert stats["cases_with_rework"] == 1145
    assert stats["unique_traces"] == 1194
    assert abs(stats["global_rework_pct"] - 20.06) < 0.1
    assert abs(stats["variability_pct"] - 89.91) < 0.1
