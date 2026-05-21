from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.users import AuditLog, RefreshToken, User


async def _create_user(
    db: AsyncSession,
    username: str = "ivanov",
    password: str = "secret123",
    role: str = "analyst",
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        full_name="Иван Иванов",
        email=f"{username}@example.com",
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_login_success(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "secret123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] == 3600
    assert data["user"]["username"] == "ivanov"
    assert data["user"]["role"] == "analyst"


async def test_login_wrong_password(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client) -> None:
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "x"}
    )
    assert resp.status_code == 401


async def test_login_inactive_user(client, db_session) -> None:
    await _create_user(db_session, "blocked", "secret123", is_active=False)
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "blocked", "password": "secret123"}
    )
    assert resp.status_code == 403


async def test_login_failed_writes_audit_log(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    await client.post("/api/v1/auth/login", json={"username": "ivanov", "password": "bad"})
    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "user.login.failed" in actions


async def test_login_success_writes_audit_log(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "secret123"}
    )
    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "user.login.success" in actions


async def test_refresh_success(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "secret123"}
    )
    refresh_token = login.json()["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_revoked_token(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "secret123"}
    )
    old_refresh = login.json()["refresh_token"]
    # Первый refresh ротирует токен — старый становится отозванным.
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


async def test_refresh_garbage_token(client) -> None:
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401


async def test_me_returns_current_user(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "secret123"}
    )
    access_token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "ivanov"


async def test_me_without_token(client) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client, db_session) -> None:
    await _create_user(db_session, "ivanov", "secret123")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "ivanov", "password": "secret123"}
    )
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 204

    stored = await db_session.scalar(select(RefreshToken))
    assert stored is not None
    assert stored.revoked_at is not None

    # Отозванный токен больше нельзя обновить.
    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 401
