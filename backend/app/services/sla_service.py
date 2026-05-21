from datetime import date

from fastapi import Request
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.db.models.projects import Project, SLARule
from app.db.models.users import User
from app.schemas.sla import SLARuleCreate, SLARuleUpdate
from app.services import audit_service


async def list_rules(
    db: AsyncSession,
    project_id: int,
    *,
    active_only: bool = False,
    role: str | None = None,
) -> tuple[list[SLARule], int]:
    conditions: list[ColumnElement[bool]] = [SLARule.project_id == project_id]
    if role is not None:
        conditions.append(SLARule.role == role)
    if active_only:
        today = date.today()
        conditions.append(SLARule.effective_from <= today)
        conditions.append(
            or_(SLARule.effective_until.is_(None), SLARule.effective_until > today)
        )
    stmt = select(SLARule).where(*conditions).order_by(SLARule.role, SLARule.id)
    items = list((await db.scalars(stmt)).all())
    return items, len(items)


async def get_rule(db: AsyncSession, rule_id: int) -> SLARule:
    rule = await db.get(SLARule, rule_id)
    if rule is None:
        raise EntityNotFoundError(f"SLA-правило с id={rule_id} не найдено")
    return rule


async def _ensure_can_modify(db: AsyncSession, project_id: int, actor: User) -> None:
    if actor.role == "admin":
        return
    project = await db.get(Project, project_id)
    if project is None or project.created_by != actor.id:
        raise PermissionDeniedError(
            "Изменять SLA-справочник может только владелец проекта или администратор"
        )


async def create_rule(
    db: AsyncSession,
    project_id: int,
    data: SLARuleCreate,
    actor: User,
    request: Request | None = None,
) -> SLARule:
    rule = SLARule(
        project_id=project_id,
        role=data.role,
        operation_pattern=data.operation_pattern,
        sla_value=data.sla_value,
        sla_unit=data.sla_unit,
        tolerance_hours=data.tolerance_hours,
        target_compliance_pct=data.target_compliance_pct,
        effective_from=data.effective_from,
        effective_until=data.effective_until,
        description=data.description,
        created_by=actor.id,
    )
    db.add(rule)
    await db.flush()
    await audit_service.log_event(
        db, actor, "sla_rule.create", "sla_rule", rule.id, request=request
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(
    db: AsyncSession,
    rule_id: int,
    data: SLARuleUpdate,
    actor: User,
    request: Request | None = None,
) -> SLARule:
    rule = await get_rule(db, rule_id)
    await _ensure_can_modify(db, rule.project_id, actor)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await audit_service.log_event(
        db, actor, "sla_rule.update", "sla_rule", rule_id, request=request
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(
    db: AsyncSession, rule_id: int, actor: User, request: Request | None = None
) -> None:
    """Мягкое удаление: effective_until = сегодня (правило перестаёт действовать)."""
    rule = await get_rule(db, rule_id)
    await _ensure_can_modify(db, rule.project_id, actor)
    rule.effective_until = date.today()
    await audit_service.log_event(
        db, actor, "sla_rule.delete", "sla_rule", rule_id, request=request
    )
    await db.commit()
