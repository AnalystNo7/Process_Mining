"""Глобальный справочник базовых ролей и шаблонов авторазметки (см. T39).

Модель: одна таблица core.global_role_templates со встроенным массивом
patterns (подстроковый матчинг, см. domain.mining.role_mapping). Используется
как стартовая точка автопредложения ролей при разметке подразделений."""

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, EntityNotFoundError
from app.db.models.projects import GlobalRoleTemplate
from app.db.models.users import User
from app.schemas.global_roles import GlobalRoleTemplateCreate, GlobalRoleTemplateUpdate
from app.services import audit_service


async def list_templates(db: AsyncSession) -> list[GlobalRoleTemplate]:
    stmt = select(GlobalRoleTemplate).order_by(
        GlobalRoleTemplate.sort_order, GlobalRoleTemplate.id
    )
    return list((await db.scalars(stmt)).all())


async def get_template(db: AsyncSession, template_id: int) -> GlobalRoleTemplate:
    template = await db.get(GlobalRoleTemplate, template_id)
    if template is None:
        raise EntityNotFoundError(f"Шаблон роли с id={template_id} не найден")
    return template


async def _ensure_unique_name(
    db: AsyncSession, role_name: str, *, exclude_id: int | None = None
) -> None:
    existing = await db.scalar(
        select(GlobalRoleTemplate).where(GlobalRoleTemplate.role_name == role_name)
    )
    if existing is not None and existing.id != exclude_id:
        raise BusinessRuleError(f"Роль {role_name!r} уже существует в справочнике")


async def create_template(
    db: AsyncSession,
    data: GlobalRoleTemplateCreate,
    actor: User,
    request: Request | None = None,
) -> GlobalRoleTemplate:
    await _ensure_unique_name(db, data.role_name)
    template = GlobalRoleTemplate(
        role_name=data.role_name,
        patterns=data.patterns,
        sort_order=data.sort_order,
        is_active=data.is_active,
        updated_by=actor.id,
    )
    db.add(template)
    await db.flush()
    await audit_service.log_event(
        db, actor, "global_role_template.create",
        "global_role_template", template.id, request=request,
    )
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    db: AsyncSession,
    template_id: int,
    data: GlobalRoleTemplateUpdate,
    actor: User,
    request: Request | None = None,
) -> GlobalRoleTemplate:
    template = await get_template(db, template_id)
    fields = data.model_dump(exclude_unset=True)
    if "role_name" in fields:
        await _ensure_unique_name(db, fields["role_name"], exclude_id=template_id)
    for field, value in fields.items():
        setattr(template, field, value)
    template.updated_by = actor.id
    await audit_service.log_event(
        db, actor, "global_role_template.update",
        "global_role_template", template_id, request=request,
    )
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(
    db: AsyncSession, template_id: int, actor: User, request: Request | None = None
) -> None:
    template = await get_template(db, template_id)
    await db.delete(template)
    await audit_service.log_event(
        db, actor, "global_role_template.delete",
        "global_role_template", template_id, request=request,
    )
    await db.commit()
