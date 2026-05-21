import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.models.users import AuditLog, User
from app.services import ldap_service
from app.services.ldap_service import LdapUserInfo


async def test_ldap_disabled_returns_503(client) -> None:
    """LDAP выключен по умолчанию — попытка LDAP-входа даёт 503."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "ivanov", "password": "pw", "use_ldap": True},
    )
    assert resp.status_code == 503


async def test_ldap_login_success_creates_user(
    client, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "LDAP_ENABLED", True)
    monkeypatch.setattr(
        ldap_service,
        "authenticate_ldap",
        lambda u, p: LdapUserInfo(username=u, full_name="ЛДАП Пользователь", email="l@ex.com"),
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "ldapuser", "password": "pw", "use_ldap": True},
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "ldapuser"
    assert resp.json()["user"]["role"] == "analyst"

    user = await db_session.scalar(select(User).where(User.username == "ldapuser"))
    assert user is not None
    assert user.is_ldap is True
    assert user.password_hash is None
    assert user.role == "analyst"


async def test_ldap_login_wrong_password(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "LDAP_ENABLED", True)
    monkeypatch.setattr(ldap_service, "authenticate_ldap", lambda u, p: None)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "ldapuser", "password": "bad", "use_ldap": True},
    )
    assert resp.status_code == 401


async def test_ldap_login_existing_user_updates_last_login(
    client, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "LDAP_ENABLED", True)
    monkeypatch.setattr(
        ldap_service,
        "authenticate_ldap",
        lambda u, p: LdapUserInfo(username=u, full_name="X", email=None),
    )
    first = await client.post(
        "/api/v1/auth/login",
        json={"username": "ldapuser", "password": "pw", "use_ldap": True},
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/auth/login",
        json={"username": "ldapuser", "password": "pw", "use_ldap": True},
    )
    assert second.status_code == 200

    users = (
        await db_session.scalars(select(User).where(User.username == "ldapuser"))
    ).all()
    assert len(users) == 1
    assert users[0].last_login_at is not None


async def test_ldap_login_writes_audit_log(
    client, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "LDAP_ENABLED", True)
    monkeypatch.setattr(
        ldap_service,
        "authenticate_ldap",
        lambda u, p: LdapUserInfo(username=u, full_name="X", email=None),
    )
    await client.post(
        "/api/v1/auth/login",
        json={"username": "ldapuser", "password": "pw", "use_ldap": True},
    )
    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "user.login.success" in actions
