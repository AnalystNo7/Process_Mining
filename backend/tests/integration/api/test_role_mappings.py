from app.db.models.projects import GlobalRoleTemplate


async def _create_project(client, headers) -> int:
    resp = await client.post("/api/v1/projects", headers=headers, json={"name": "Проект"})
    return int(resp.json()["id"])


async def test_get_current_mapping_exists_after_project_create(
    client, analyst_user
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 1
    assert data["mapping"] == {}


async def test_put_creates_new_version(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.put(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
        json={
            "mapping": {"Юридическое управление": "Юридическое управление"},
            "roles": ["Юридическое управление"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    current = await client.get(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
    )
    assert current.json()["version"] == 2
    assert current.json()["mapping"]["Юридическое управление"] == "Юридическое управление"


async def test_put_requires_owner_or_admin(client, analyst_user, admin_user) -> None:
    project_id = await _create_project(client, admin_user.headers)
    resp = await client.put(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
        json={"mapping": {}, "roles": []},
    )
    assert resp.status_code == 403


async def test_suggest_roles(client, analyst_user, db_session) -> None:
    db_session.add(
        GlobalRoleTemplate(
            role_name="Юридическое управление",
            patterns=["Юридическое управление", "ЮУ"],
            sort_order=10,
            is_active=True,
        )
    )
    await db_session.commit()
    project_id = await _create_project(client, analyst_user.headers)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/role-mappings/suggest",
        headers=analyst_user.headers,
        json={"departments": ["ЮУ Москва", "Проект 5"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suggestions"]["ЮУ Москва"]["role"] == "Юридическое управление"
    assert data["suggestions"]["Проект 5"]["role"] == "Не размечено"
    assert "Юридическое управление" in data["available_roles"]


async def test_history(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    await client.put(
        f"/api/v1/projects/{project_id}/role-mappings/current",
        headers=analyst_user.headers,
        json={"mapping": {}, "roles": []},
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/role-mappings/history",
        headers=analyst_user.headers,
    )
    assert resp.status_code == 200
    versions = [item["version"] for item in resp.json()]
    assert versions == [2, 1]
