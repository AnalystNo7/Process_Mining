from app.db.models.datasets import PhysicalDataset


async def _setup_vd(client, headers, db, user_id: int) -> tuple[int, int]:
    project = await client.post("/api/v1/projects", headers=headers, json={"name": "P"})
    project_id = int(project.json()["id"])
    dataset = PhysicalDataset(
        project_id=project_id, name="DS", file_name="f.xlsx", file_size_bytes=1,
        file_hash="h", storage_path="", column_mapping={}, total_events=0,
        total_cases=0, unique_activities=0, health_status="good", health_report={},
        uploaded_by=user_id, status="ready",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    vd = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=headers,
        json={"name": "VD", "physical_dataset_id": dataset.id},
    )
    return project_id, int(vd.json()["id"])


async def test_create_and_list_slices(client, analyst_user, db_session) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/slices",
        headers=analyst_user.headers,
        json={"name": "Затяжные кейсы", "filters": {"case_duration": {"min_days": 30}}},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Затяжные кейсы"

    listing = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/slices",
        headers=analyst_user.headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


async def test_update_slice(client, analyst_user, db_session) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/slices",
        headers=analyst_user.headers,
        json={"name": "Срез", "filters": {}},
    )
    slice_id = created.json()["id"]
    patched = await client.patch(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/slices/{slice_id}",
        headers=analyst_user.headers,
        json={"name": "Обновлённый срез"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Обновлённый срез"


async def test_delete_slice_resets_dashboard_applied_slice(
    client, analyst_user, db_session
) -> None:
    project_id, vd_id = await _setup_vd(
        client, analyst_user.headers, db_session, analyst_user.id
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/slices",
        headers=analyst_user.headers,
        json={"name": "Срез", "filters": {}},
    )
    slice_id = created.json()["id"]

    dashboards = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
    )
    dashboard_id = dashboards.json()["items"][0]["id"]
    await client.patch(
        f"/api/v1/dashboards/{dashboard_id}",
        headers=analyst_user.headers,
        json={"applied_slice_id": slice_id},
    )

    deleted = await client.delete(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/slices/{slice_id}",
        headers=analyst_user.headers,
    )
    assert deleted.status_code == 204

    # Дашборд не сломался — applied_slice_id сброшен в NULL (FK ON DELETE SET NULL).
    detail = await client.get(
        f"/api/v1/dashboards/{dashboard_id}", headers=analyst_user.headers
    )
    assert detail.status_code == 200
    assert detail.json()["applied_slice_id"] is None
