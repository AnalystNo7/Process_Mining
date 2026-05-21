from datetime import date
from typing import Any

from fastapi import Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.db.models.datasets import PhysicalDataset, VirtualDataset
from app.db.models.projects import SLARule
from app.db.models.users import User
from app.db.repositories.event_log import PostgresEventLogRepository
from app.domain.mining.role_mapping import apply_role_mapping, get_activity_breakdown
from app.schemas.virtual_datasets import (
    ActivityBreakdownResponse,
    BreakdownItem,
    RoleBreakdownResponse,
    VirtualDatasetCreate,
)
from app.services import audit_service, role_mapping_service


async def _sla_snapshot(db: AsyncSession, project_id: int) -> list[dict[str, Any]]:
    """Снимок действующих на сегодня SLA-правил проекта."""
    today = date.today()
    rules = (
        await db.scalars(
            select(SLARule).where(
                SLARule.project_id == project_id,
                SLARule.effective_from <= today,
                or_(
                    SLARule.effective_until.is_(None),
                    SLARule.effective_until > today,
                ),
            )
        )
    ).all()
    return [
        {
            "id": r.id,
            "role": r.role,
            "operation_pattern": r.operation_pattern,
            "sla_value": float(r.sla_value),
            "sla_unit": r.sla_unit,
            "tolerance_hours": float(r.tolerance_hours),
            "target_compliance_pct": float(r.target_compliance_pct),
        }
        for r in rules
    ]


async def create_virtual_dataset(
    db: AsyncSession,
    project_id: int,
    payload: VirtualDatasetCreate,
    actor: User,
    request: Request | None = None,
) -> VirtualDataset:
    """Создаёт виртуальный датасет с immutable-снимком маппинга ролей и SLA."""
    physical = await db.get(PhysicalDataset, payload.physical_dataset_id)
    if physical is None or physical.project_id != project_id:
        raise EntityNotFoundError(
            f"Физический датасет {payload.physical_dataset_id} не найден в проекте"
        )

    role_mapping = await role_mapping_service.get_current_mapping(db, project_id)

    virtual = VirtualDataset(
        project_id=project_id,
        physical_dataset_id=payload.physical_dataset_id,
        name=payload.name,
        description=payload.description,
        role_mapping_snapshot={
            "version": role_mapping.version,
            "mapping": role_mapping.mapping,
            "roles": role_mapping.roles,
        },
        sla_rules_snapshot=await _sla_snapshot(db, project_id),
        config=payload.config,
        cached_stats=None,
        created_by=actor.id,
        is_personal=True,
    )
    db.add(virtual)
    await audit_service.log_event(
        db, actor, "virtual_dataset.create", "virtual_dataset", None, request=request,
        metadata={"name": virtual.name},
    )
    await db.commit()
    await db.refresh(virtual)
    # Фоновый расчёт cached_stats подключается в задаче T16.
    return virtual


async def get_virtual_dataset(
    db: AsyncSession, project_id: int, vd_id: int
) -> VirtualDataset:
    virtual = await db.get(VirtualDataset, vd_id)
    if virtual is None or virtual.project_id != project_id:
        raise EntityNotFoundError(f"Виртуальный датасет с id={vd_id} не найден")
    return virtual


async def list_virtual_datasets(
    db: AsyncSession, project_id: int
) -> tuple[list[VirtualDataset], int]:
    stmt = (
        select(VirtualDataset)
        .where(VirtualDataset.project_id == project_id)
        .order_by(VirtualDataset.created_at.desc())
    )
    items = list((await db.scalars(stmt)).all())
    return items, len(items)


async def delete_virtual_dataset(
    db: AsyncSession,
    project_id: int,
    vd_id: int,
    actor: User,
    request: Request | None = None,
) -> None:
    virtual = await get_virtual_dataset(db, project_id, vd_id)
    if actor.role != "admin" and virtual.created_by != actor.id:
        raise PermissionDeniedError(
            "Удалять виртуальный датасет может только создатель или администратор"
        )
    await db.delete(virtual)
    await audit_service.log_event(
        db, actor, "virtual_dataset.delete", "virtual_dataset", vd_id, request=request
    )
    await db.commit()


async def role_breakdown(
    db: AsyncSession, project_id: int, vd_id: int, role: str
) -> RoleBreakdownResponse:
    """Drill-down: какие подразделения входят в роль."""
    virtual = await get_virtual_dataset(db, project_id, vd_id)
    repo = PostgresEventLogRepository(db)
    df = await repo.load_to_dataframe(virtual.physical_dataset_id)
    df = apply_role_mapping(df, virtual.role_mapping_snapshot.get("mapping", {}))
    subset = df[df["role"] == role]
    grouped = (
        subset.groupby("department")
        .agg(events=("case_id", "count"), cases=("case_id", "nunique"))
        .reset_index()
        .sort_values("events", ascending=False)
    )
    return RoleBreakdownResponse(
        role=role,
        departments=[
            BreakdownItem(
                name=str(row["department"]),
                events=int(row["events"]),
                cases=int(row["cases"]),
            )
            for _, row in grouped.iterrows()
        ],
        total_events=int(len(subset)),
        total_cases=int(subset["case_id"].nunique()),
    )


async def activity_breakdown(
    db: AsyncSession, project_id: int, vd_id: int, activity_with_role: str
) -> ActivityBreakdownResponse:
    """Drill-down: из каких сырых операций составлена роль-операция."""
    virtual = await get_virtual_dataset(db, project_id, vd_id)
    repo = PostgresEventLogRepository(db)
    df = await repo.load_to_dataframe(virtual.physical_dataset_id)
    df = apply_role_mapping(df, virtual.role_mapping_snapshot.get("mapping", {}))
    breakdown = get_activity_breakdown(df, activity_with_role)
    return ActivityBreakdownResponse(
        activity_with_role=activity_with_role,
        operations=[
            BreakdownItem(
                name=str(row["activity"]),
                events=int(row["events"]),
                cases=int(row["cases"]),
            )
            for _, row in breakdown.iterrows()
        ],
        total_events=int(breakdown["events"].sum()) if len(breakdown) else 0,
        total_cases=int(breakdown["cases"].sum()) if len(breakdown) else 0,
    )
