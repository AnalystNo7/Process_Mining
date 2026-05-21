async def test_audit_log_admin_only(client, analyst_user) -> None:
    resp = await client.get("/api/v1/admin/audit-log", headers=analyst_user.headers)
    assert resp.status_code == 403


async def test_audit_log_without_token(client) -> None:
    resp = await client.get("/api/v1/admin/audit-log")
    assert resp.status_code == 401


async def test_audit_log_records_login(client, admin_user) -> None:
    # admin_user уже создан; выполняем вход, чтобы появилась запись.
    await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "password123"}
    )
    resp = await client.get("/api/v1/admin/audit-log", headers=admin_user.headers)
    assert resp.status_code == 200
    actions = [item["action"] for item in resp.json()["items"]]
    assert "user.login.success" in actions


async def test_audit_log_records_user_create(client, admin_user) -> None:
    await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "auditee", "role": "analyst", "password": "secret12345"},
    )
    resp = await client.get(
        "/api/v1/admin/audit-log", headers=admin_user.headers, params={"action": "user.create"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["action"] == "user.create" for item in data["items"])
    assert data["items"][0]["user"]["username"] == "admin"


async def test_audit_log_filter_by_action(client, admin_user) -> None:
    await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "password123"}
    )
    resp = await client.get(
        "/api/v1/admin/audit-log", headers=admin_user.headers, params={"action": "login"}
    )
    assert resp.status_code == 200
    assert all("login" in item["action"] for item in resp.json()["items"])


async def test_audit_log_filter_by_user(client, admin_user) -> None:
    await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "byuser", "role": "analyst", "password": "secret12345"},
    )
    resp = await client.get(
        "/api/v1/admin/audit-log",
        headers=admin_user.headers,
        params={"user_id": admin_user.id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["user"]["id"] == admin_user.id for item in data["items"])


async def test_audit_log_pagination(client, admin_user) -> None:
    for i in range(3):
        await client.post(
            "/api/v1/users",
            headers=admin_user.headers,
            json={"username": f"page{i}", "role": "analyst", "password": "secret12345"},
        )
    resp = await client.get(
        "/api/v1/admin/audit-log",
        headers=admin_user.headers,
        params={"page": 1, "page_size": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3
    assert data["page_size"] == 2
