from typing import Any

_URL = "/api/v1/admin/global-role-templates"


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role_name": "Юридическое управление",
        "patterns": ["Юр.управление", "ЮУ"],
        "sort_order": 10,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


async def test_only_admin_can_access_global_templates(client, analyst_user) -> None:
    resp = await client.get(_URL, headers=analyst_user.headers)
    assert resp.status_code == 403


async def test_create_and_list_global_role_template(client, admin_user) -> None:
    created = await client.post(_URL, headers=admin_user.headers, json=_payload())
    assert created.status_code == 201
    assert created.json()["role_name"] == "Юридическое управление"

    listing = await client.get(_URL, headers=admin_user.headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["patterns"] == ["Юр.управление", "ЮУ"]


async def test_create_duplicate_role_name_conflict(client, admin_user) -> None:
    await client.post(_URL, headers=admin_user.headers, json=_payload())
    duplicate = await client.post(
        _URL, headers=admin_user.headers, json=_payload(patterns=[])
    )
    assert duplicate.status_code == 409


async def test_update_global_role_template(client, admin_user) -> None:
    created = await client.post(_URL, headers=admin_user.headers, json=_payload())
    template_id = created.json()["id"]
    resp = await client.put(
        f"{_URL}/{template_id}",
        headers=admin_user.headers,
        json={"is_active": False, "patterns": ["правовой поддержки"]},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["patterns"] == ["правовой поддержки"]


async def test_update_global_role_template_not_found(client, admin_user) -> None:
    resp = await client.put(
        f"{_URL}/999999", headers=admin_user.headers, json={"is_active": False}
    )
    assert resp.status_code == 404


async def test_delete_global_role_template(client, admin_user) -> None:
    created = await client.post(_URL, headers=admin_user.headers, json=_payload())
    template_id = created.json()["id"]
    resp = await client.delete(f"{_URL}/{template_id}", headers=admin_user.headers)
    assert resp.status_code == 204

    listing = await client.get(_URL, headers=admin_user.headers)
    assert listing.json()["total"] == 0
