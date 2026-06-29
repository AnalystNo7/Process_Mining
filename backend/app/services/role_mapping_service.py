from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, EntityNotFoundError
from app.db.models.projects import GlobalRoleTemplate, RoleMapping
from app.db.models.users import User
from app.domain.mining.role_mapping import (
    UNMAPPED_ROLE,
    find_unmapped_departments,
    suggest_role_mapping,
)
from app.schemas.role_mappings import SuggestionItem
from app.services import audit_service


async def get_current_mapping(db: AsyncSession, project_id: int) -> RoleMapping:
    """Возвращает последнюю версию маппинга ролей проекта."""
    mapping = await db.scalar(
        select(RoleMapping)
        .where(RoleMapping.project_id == project_id)
        .order_by(RoleMapping.version.desc())
        .limit(1)
    )
    if mapping is None:
        raise EntityNotFoundError(f"У проекта {project_id} нет маппинга ролей")
    return mapping


async def get_history(db: AsyncSession, project_id: int) -> list[RoleMapping]:
    stmt = (
        select(RoleMapping)
        .where(RoleMapping.project_id == project_id)
        .order_by(RoleMapping.version.desc())
    )
    return list((await db.scalars(stmt)).all())


async def _global_templates(db: AsyncSession) -> list[dict[str, Any]]:
    stmt = (
        select(GlobalRoleTemplate)
        .where(GlobalRoleTemplate.is_active.is_(True))
        .order_by(GlobalRoleTemplate.sort_order)
    )
    rows = (await db.scalars(stmt)).all()
    return [{"role_name": r.role_name, "patterns": r.patterns} for r in rows]


async def suggest(
    db: AsyncSession, departments: list[str]
) -> tuple[dict[str, SuggestionItem], list[str]]:
    """Авто-предложение ролей для подразделений по глобальным шаблонам."""
    templates = await _global_templates(db)
    raw = suggest_role_mapping(departments, templates)
    suggestions = {
        dept: SuggestionItem(role=role, matched_pattern=pattern)
        for dept, (role, pattern) in raw.items()
    }
    available_roles = [str(t["role_name"]) for t in templates] + [UNMAPPED_ROLE]
    return suggestions, available_roles


async def update_mapping(
    db: AsyncSession,
    project_id: int,
    mapping: dict[str, str],
    roles: list[str],
    actor: User,
    request: Request | None = None,
) -> RoleMapping:
    """Сохраняет маппинг как новую версию (старые версии не удаляются).

    Бизнес-правило: нельзя сохранить, пока хотя бы одно подразделение не
    сопоставлено роли (пусто или «Не размечено»)."""
    unmapped = find_unmapped_departments(mapping)
    if unmapped:
        raise BusinessRuleError(
            f"Роли не размечены: {len(unmapped)} подразделений"
        )
    current = await get_current_mapping(db, project_id)
    new_version = RoleMapping(
        project_id=project_id,
        name=current.name,
        version=current.version + 1,
        mapping=mapping,
        roles=roles,
    )
    db.add(new_version)
    await audit_service.log_event(
        db, actor, "role_mapping.update", "role_mapping", project_id, request=request,
        metadata={"version": current.version + 1},
    )
    await db.commit()
    await db.refresh(new_version)
    return new_version


async def ensure_departments_mapped(
    db: AsyncSession, project_id: int, departments: list[str]
) -> None:
    """Добавляет новые подразделения в маппинг с ролью 'Не размечено'
    (новая версия). Commit выполняет вызывающий код."""
    current = await db.scalar(
        select(RoleMapping)
        .where(RoleMapping.project_id == project_id)
        .order_by(RoleMapping.version.desc())
        .limit(1)
    )
    if current is None:
        return
    new_departments = sorted(
        {d for d in departments if d and d not in current.mapping}
    )
    if not new_departments:
        return
    updated_mapping = dict(current.mapping)
    for dept in new_departments:
        updated_mapping[dept] = UNMAPPED_ROLE
    db.add(
        RoleMapping(
            project_id=project_id,
            name=current.name,
            version=current.version + 1,
            mapping=updated_mapping,
            roles=current.roles,
        )
    )
