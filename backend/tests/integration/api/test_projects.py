from sqlalchemy import select

from app.db.models.projects import Project, RoleMapping, UploadTemplate
from app.db.models.users import AuditLog


async def _create_project(client, headers, name: str = "Согласование договоров") -> int:
    resp = await client.post(
        "/api/v1/projects", headers=headers, json={"name": name, "description": "TESSA"}
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def test_create_project(client, analyst_user, db_session) -> None:
    resp = await client.post(
        "/api/v1/projects",
        headers=analyst_user.headers,
        json={"name": "Тестовый проект", "description": "описание"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Тестовый проект"
    assert data["created_by"]["username"] == "analyst"
    assert data["physical_datasets_count"] == 0

    actions = (await db_session.scalars(select(AuditLog.action))).all()
    assert "project.create" in actions


async def test_create_project_creates_default_template_and_mapping(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)

    mapping = await db_session.scalar(
        select(RoleMapping).where(RoleMapping.project_id == project_id)
    )
    assert mapping is not None
    assert mapping.version == 1

    template = await db_session.scalar(
        select(UploadTemplate).where(UploadTemplate.project_id == project_id)
    )
    assert template is not None
    assert template.column_mapping["case_id"] == "doc_id"
    assert template.is_default is True


async def test_list_projects_returns_all(client, analyst_user, admin_user) -> None:
    await _create_project(client, analyst_user.headers, "Проект аналитика")
    await _create_project(client, admin_user.headers, "Проект админа")

    resp = await client.get("/api/v1/projects", headers=analyst_user.headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_list_projects_requires_auth(client) -> None:
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401


async def test_get_project(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.get(f"/api/v1/projects/{project_id}", headers=analyst_user.headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id


async def test_get_project_not_found(client, analyst_user) -> None:
    resp = await client.get("/api/v1/projects/999999", headers=analyst_user.headers)
    assert resp.status_code == 404


async def test_update_project_owner_can(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=analyst_user.headers,
        json={"name": "Переименованный"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Переименованный"


async def test_update_project_other_analyst_forbidden(
    client, analyst_user, db_session
) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    # Второй аналитик.
    from app.core.security import create_access_token, hash_password
    from app.db.models.users import User

    other = User(
        username="other",
        full_name="Другой",
        role="analyst",
        is_active=True,
        password_hash=hash_password("password123"),
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    token = create_access_token(other.id, {"role": "analyst"})

    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Взлом"},
    )
    assert resp.status_code == 403


async def test_update_project_admin_can(client, analyst_user, admin_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=admin_user.headers,
        json={"description": "изменено админом"},
    )
    assert resp.status_code == 200


async def test_delete_project_soft_delete(client, analyst_user, db_session) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    resp = await client.delete(
        f"/api/v1/projects/{project_id}", headers=analyst_user.headers
    )
    assert resp.status_code == 204

    project = await db_session.get(Project, project_id)
    assert project is not None
    assert project.is_deleted is True


async def test_deleted_project_not_in_list(client, analyst_user) -> None:
    project_id = await _create_project(client, analyst_user.headers)
    await client.delete(f"/api/v1/projects/{project_id}", headers=analyst_user.headers)

    resp = await client.get("/api/v1/projects", headers=analyst_user.headers)
    assert resp.json()["total"] == 0

    detail = await client.get(
        f"/api/v1/projects/{project_id}", headers=analyst_user.headers
    )
    assert detail.status_code == 404
