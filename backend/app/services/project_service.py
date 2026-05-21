from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.db.models.dashboards import Dashboard
from app.db.models.datasets import PhysicalDataset, VirtualDataset
from app.db.models.projects import Project, RoleMapping, UploadTemplate
from app.db.models.users import User
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services import audit_service

# Стандартный маппинг колонок выгрузки TESSA — создаётся при создании проекта.
DEFAULT_TESSA_TEMPLATE: dict[str, Any] = {
    "case_id": "doc_id",
    "activity": "Операция",
    "timestamp_start": "in_progress_datetime",
    "timestamp_end": "completed_datetime",
    "resource": "task_user",
    "department": "task_user_department",
    "additional": {
        "doc_type": "doc_type",
        "doc_number": "doc_number",
        "kr_state": "kr_state",
        "head_user_name": "head_user_name",
        "route_type": "route_type",
        "group_name": "group_name",
    },
}


async def project_counts(
    db: AsyncSession, project_ids: list[int]
) -> dict[int, tuple[int, int, int]]:
    """Возвращает {project_id: (физ.датасеты, вирт.датасеты, дашборды)}."""
    if not project_ids:
        return {}
    phys: dict[int, int] = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(PhysicalDataset.project_id, func.count())
                .where(PhysicalDataset.project_id.in_(project_ids))
                .group_by(PhysicalDataset.project_id)
            )
        ).all()
    }
    virt: dict[int, int] = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(VirtualDataset.project_id, func.count())
                .where(VirtualDataset.project_id.in_(project_ids))
                .group_by(VirtualDataset.project_id)
            )
        ).all()
    }
    dash: dict[int, int] = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(VirtualDataset.project_id, func.count(Dashboard.id))
                .join(Dashboard, Dashboard.virtual_dataset_id == VirtualDataset.id)
                .where(VirtualDataset.project_id.in_(project_ids))
                .group_by(VirtualDataset.project_id)
            )
        ).all()
    }
    return {
        pid: (phys.get(pid, 0), virt.get(pid, 0), dash.get(pid, 0)) for pid in project_ids
    }


async def list_projects(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    created_by: int | None = None,
) -> tuple[list[tuple[Project, User]], int]:
    conditions: list[ColumnElement[bool]] = [Project.is_deleted.is_(False)]
    if search:
        conditions.append(Project.name.ilike(f"%{search}%"))
    if created_by is not None:
        conditions.append(Project.created_by == created_by)

    total = await db.scalar(
        select(func.count()).select_from(Project).where(*conditions)
    ) or 0
    stmt = (
        select(Project, User)
        .join(User, Project.created_by == User.id)
        .where(*conditions)
        .order_by(Project.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = [(row[0], row[1]) for row in (await db.execute(stmt)).all()]
    return rows, total


async def get_project_with_owner(db: AsyncSession, project_id: int) -> tuple[Project, User]:
    row = (
        await db.execute(
            select(Project, User)
            .join(User, Project.created_by == User.id)
            .where(Project.id == project_id, Project.is_deleted.is_(False))
        )
    ).first()
    if row is None:
        raise EntityNotFoundError(f"Проект с id={project_id} не найден")
    return row[0], row[1]


async def create_project(
    db: AsyncSession, data: ProjectCreate, actor: User, request: Request | None = None
) -> Project:
    project = Project(name=data.name, description=data.description, created_by=actor.id)
    db.add(project)
    await db.flush()

    # Общие сущности проекта: пустой маппинг ролей v1 + шаблон загрузки TESSA.
    db.add(
        RoleMapping(
            project_id=project.id,
            name="Основной маппинг",
            version=1,
            mapping={},
            roles=[],
        )
    )
    db.add(
        UploadTemplate(
            project_id=project.id,
            name="Стандартный шаблон TESSA",
            column_mapping=DEFAULT_TESSA_TEMPLATE,
            is_default=True,
        )
    )
    await audit_service.log_event(
        db, actor, "project.create", "project", project.id, request=request,
        metadata={"name": project.name},
    )
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession,
    project: Project,
    data: ProjectUpdate,
    actor: User,
    request: Request | None = None,
) -> Project:
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    await audit_service.log_event(
        db, actor, "project.update", "project", project.id, request=request
    )
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(
    db: AsyncSession, project: Project, actor: User, request: Request | None = None
) -> None:
    """Мягкое удаление проекта."""
    project.is_deleted = True
    project.deleted_at = datetime.now(timezone.utc)
    await audit_service.log_event(
        db, actor, "project.delete", "project", project.id, request=request
    )
    await db.commit()
