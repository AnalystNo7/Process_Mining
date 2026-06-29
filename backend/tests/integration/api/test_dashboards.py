


async def _create_project(client, headers) -> int:
    resp = await client.post("/api/v1/projects", headers=headers, json={"name": "P"})
    return int(resp.json()["id"])


async def _make_physical(db, project_id: int, uploaded_by: int) -> int:
    from app.db.models.datasets import PhysicalDataset

    dataset = PhysicalDataset(
        project_id=project_id, name="DS", file_name="f.xlsx", file_size_bytes=1,
        file_hash="h", storage_path="", column_mapping={}, total_events=0,
        total_cases=0, unique_activities=0, health_status="good", health_report={},
        uploaded_by=uploaded_by, status="ready",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset.id


async def _create_vd(client, headers, project_id: int, physical_id: int) -> int:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets",
        headers=headers,
        json={"name": "VD", "physical_dataset_id": physical_id},
    )
    return int(resp.json()["id"])


async def test_default_dashboard_created_with_vd(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical_id = await _make_physical(db_session, project_id, analyst_user.id)
    vd_id = await _create_vd(client, analyst_user.headers, project_id, physical_id)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["name"] == "Обзор процесса"

    dashboard_id = resp.json()["items"][0]["id"]
    detail = await client.get(
        f"/api/v1/dashboards/{dashboard_id}", headers=analyst_user.headers
    )
    assert len(detail.json()["widgets"]) == 21


async def test_dashboard_crud(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical_id = await _make_physical(db_session, project_id, analyst_user.id)
    vd_id = await _create_vd(client, analyst_user.headers, project_id, physical_id)

    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
        json={"name": "Мой дашборд"},
    )
    assert created.status_code == 201
    dashboard_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/dashboards/{dashboard_id}",
        headers=analyst_user.headers,
        json={"name": "Переименован"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Переименован"

    deleted = await client.delete(
        f"/api/v1/dashboards/{dashboard_id}", headers=analyst_user.headers
    )
    assert deleted.status_code == 204


async def test_widget_crud(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical_id = await _make_physical(db_session, project_id, analyst_user.id)
    vd_id = await _create_vd(client, analyst_user.headers, project_id, physical_id)
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
        json={"name": "D"},
    )
    dashboard_id = created.json()["id"]

    widget = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        headers=analyst_user.headers,
        json={"widget_type": "kpi_card", "title": "Кейсы",
              "config": {"metric": "total_cases"}},
    )
    assert widget.status_code == 201
    widget_id = widget.json()["id"]

    patched = await client.patch(
        f"/api/v1/widgets/{widget_id}",
        headers=analyst_user.headers,
        json={"title": "Всего кейсов"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Всего кейсов"

    deleted = await client.delete(
        f"/api/v1/widgets/{widget_id}", headers=analyst_user.headers
    )
    assert deleted.status_code == 204


async def test_update_widget_layouts_batch(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical_id = await _make_physical(db_session, project_id, analyst_user.id)
    vd_id = await _create_vd(client, analyst_user.headers, project_id, physical_id)
    listing = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
    )
    dashboard_id = listing.json()["items"][0]["id"]
    detail = await client.get(
        f"/api/v1/dashboards/{dashboard_id}", headers=analyst_user.headers
    )
    widgets = detail.json()["widgets"]
    items = [
        {"id": w["id"], "grid_x": (idx % 4) * 3, "grid_y": (idx // 4) * 2,
         "grid_width": 3, "grid_height": 2}
        for idx, w in enumerate(widgets)
    ]
    resp = await client.patch(
        f"/api/v1/dashboards/{dashboard_id}/widgets/layout",
        headers=analyst_user.headers,
        json={"widgets": items},
    )
    assert resp.status_code == 200
    by_id = {w["id"]: w for w in resp.json()["widgets"]}
    for item in items:
        assert by_id[item["id"]]["grid_x"] == item["grid_x"]
        assert by_id[item["id"]]["grid_y"] == item["grid_y"]
        assert by_id[item["id"]]["grid_width"] == 3
        assert by_id[item["id"]]["grid_height"] == 2

    # Виджет из другого дашборда не должен «прокинуться» через batch.
    other = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
        json={"name": "Other"},
    )
    other_id = other.json()["id"]
    bad = await client.patch(
        f"/api/v1/dashboards/{other_id}/widgets/layout",
        headers=analyst_user.headers,
        json={"widgets": [{"id": widgets[0]["id"], "grid_x": 0, "grid_y": 0,
                            "grid_width": 3, "grid_height": 2}]},
    )
    assert bad.status_code == 422


async def test_duplicate_dashboard_copies_widgets(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    physical_id = await _make_physical(db_session, project_id, analyst_user.id)
    vd_id = await _create_vd(client, analyst_user.headers, project_id, physical_id)
    dashboards = await client.get(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=analyst_user.headers,
    )
    source_id = dashboards.json()["items"][0]["id"]

    resp = await client.post(
        f"/api/v1/dashboards/{source_id}/duplicate", headers=analyst_user.headers
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Обзор процесса (копия)"
    assert len(resp.json()["widgets"]) == 21


async def test_dashboard_delete_other_user_forbidden(
    client, analyst_user, admin_user, db_session
) -> None:
    project_id = await _create_project(client, admin_user.headers)
    physical_id = await _make_physical(db_session, project_id, admin_user.id)
    vd_id = await _create_vd(client, admin_user.headers, project_id, physical_id)
    created = await client.post(
        f"/api/v1/projects/{project_id}/virtual-datasets/{vd_id}/dashboards",
        headers=admin_user.headers,
        json={"name": "D"},
    )
    dashboard_id = created.json()["id"]

    forbidden = await client.delete(
        f"/api/v1/dashboards/{dashboard_id}", headers=analyst_user.headers
    )
    assert forbidden.status_code == 403
