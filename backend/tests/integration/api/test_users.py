from sqlalchemy import select

from app.db.models.users import AuditLog, User


async def test_list_users_admin_can(client, admin_user) -> None:
    resp = await client.get("/api/v1/users", headers=admin_user.headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["page"] == 1
    assert any(u["username"] == "admin" for u in data["items"])


async def test_list_users_analyst_cannot(client, analyst_user) -> None:
    resp = await client.get("/api/v1/users", headers=analyst_user.headers)
    assert resp.status_code == 403


async def test_list_users_without_token(client) -> None:
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401


async def test_create_user_success(client, admin_user, db_session) -> None:
    resp = await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "petrov", "full_name": "Пётр Петров", "role": "analyst",
              "password": "secret12345"},
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "petrov"

    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "user.create" in actions


async def test_create_user_validates_password_for_non_ldap(client, admin_user) -> None:
    resp = await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "nopass", "role": "analyst"},
    )
    assert resp.status_code == 422


async def test_create_ldap_user_without_password(client, admin_user, db_session) -> None:
    resp = await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "ldapuser2", "role": "analyst", "is_ldap": True},
    )
    assert resp.status_code == 201
    user = await db_session.scalar(select(User).where(User.username == "ldapuser2"))
    assert user is not None
    assert user.is_ldap is True
    assert user.password_hash is None


async def test_create_user_duplicate_username(client, admin_user) -> None:
    payload = {"username": "duplicate", "role": "analyst", "password": "secret12345"}
    first = await client.post("/api/v1/users", headers=admin_user.headers, json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/users", headers=admin_user.headers, json=payload)
    assert second.status_code == 409


async def test_get_user_not_found(client, admin_user) -> None:
    resp = await client.get("/api/v1/users/999999", headers=admin_user.headers)
    assert resp.status_code == 404


async def test_update_user_password(client, admin_user) -> None:
    created = await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "pwuser", "role": "analyst", "password": "oldpassword1"},
    )
    user_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_user.headers,
        json={"password": "newpassword1"},
    )
    assert patched.status_code == 200

    login = await client.post(
        "/api/v1/auth/login", json={"username": "pwuser", "password": "newpassword1"}
    )
    assert login.status_code == 200


async def test_update_user_role(client, admin_user) -> None:
    created = await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "promote", "role": "analyst", "password": "secret12345"},
    )
    user_id = created.json()["id"]
    patched = await client.patch(
        f"/api/v1/users/{user_id}", headers=admin_user.headers, json={"role": "admin"}
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "admin"


async def test_deactivate_user(client, admin_user, db_session) -> None:
    created = await client.post(
        "/api/v1/users",
        headers=admin_user.headers,
        json={"username": "todelete", "role": "analyst", "password": "secret12345"},
    )
    user_id = created.json()["id"]
    resp = await client.delete(f"/api/v1/users/{user_id}", headers=admin_user.headers)
    assert resp.status_code == 204

    user = await db_session.get(User, user_id)
    assert user is not None
    assert user.is_active is False


async def test_cannot_deactivate_last_admin(client, admin_user) -> None:
    resp = await client.delete(
        f"/api/v1/users/{admin_user.id}", headers=admin_user.headers
    )
    assert resp.status_code == 422


async def test_cannot_demote_last_admin(client, admin_user) -> None:
    resp = await client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=admin_user.headers,
        json={"role": "analyst"},
    )
    assert resp.status_code == 422


async def test_list_users_filter_by_role(client, admin_user, analyst_user) -> None:
    resp = await client.get(
        "/api/v1/users", headers=admin_user.headers, params={"role": "analyst"}
    )
    assert resp.status_code == 200
    assert all(u["role"] == "analyst" for u in resp.json()["items"])
