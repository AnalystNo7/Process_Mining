from typing import Any

from app.core.security import create_access_token, hash_password
from app.db.models.users import User


def _rule_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": "ЮУ",
        "operation_pattern": "*",
        "sla_value": 3,
        "sla_unit": "workdays",
        "tolerance_hours": 0,
        "target_compliance_pct": 90.0,
        "effective_from": "2020-01-01",
    }
    payload.update(overrides)
    return payload


async def _create_project(client, headers) -> int:
    resp = await client.post("/api/v1/projects", headers=headers, json={"name": "P"})
    return int(resp.json()["id"])


async def test_create_sla_rule(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers=analyst_user.headers,
        json=_rule_payload(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "ЮУ"
    assert data["sla_unit"] == "workdays"
    assert data["project_id"] == project_id


async def test_create_sla_rule_forbidden_for_non_owner(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    other = User(
        username="other", full_name="Другой", role="analyst", is_active=True,
        password_hash=hash_password("password123"),
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    token = create_access_token(other.id, {"role": "analyst"})

    resp = await client.post(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers={"Authorization": f"Bearer {token}"},
        json=_rule_payload(),
    )
    assert resp.status_code == 403


async def test_list_sla_rules_with_role_filter(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    for role in ("ЮУ", "Финансы"):
        await client.post(
            f"/api/v1/projects/{project_id}/sla-rules",
            headers=analyst_user.headers,
            json=_rule_payload(role=role),
        )
    full = await client.get(
        f"/api/v1/projects/{project_id}/sla-rules", headers=analyst_user.headers
    )
    assert full.status_code == 200
    assert full.json()["total"] == 2

    filtered = await client.get(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers=analyst_user.headers,
        params={"role": "ЮУ"},
    )
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["role"] == "ЮУ"


async def test_update_sla_rule(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    created = await client.post(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers=analyst_user.headers,
        json=_rule_payload(),
    )
    rule_id = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/sla-rules/{rule_id}",
        headers=analyst_user.headers,
        json={"sla_value": 5, "tolerance_hours": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sla_value"] == 5
    assert data["tolerance_hours"] == 2


async def test_update_sla_rule_not_found(client, analyst_user) -> None:
    resp = await client.patch(
        "/api/v1/sla-rules/999999",
        headers=analyst_user.headers,
        json={"sla_value": 5},
    )
    assert resp.status_code == 404


async def test_delete_sla_rule_is_soft(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    created = await client.post(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers=analyst_user.headers,
        json=_rule_payload(),
    )
    rule_id = created.json()["id"]
    resp = await client.delete(
        f"/api/v1/sla-rules/{rule_id}", headers=analyst_user.headers
    )
    assert resp.status_code == 204

    # Мягкое удаление: правило выпадает из active_only, но остаётся в общем списке.
    active = await client.get(
        f"/api/v1/projects/{project_id}/sla-rules",
        headers=analyst_user.headers,
        params={"active_only": True},
    )
    assert active.json()["total"] == 0
    full = await client.get(
        f"/api/v1/projects/{project_id}/sla-rules", headers=analyst_user.headers
    )
    assert full.json()["total"] == 1
