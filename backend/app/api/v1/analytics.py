from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import EntityNotFoundError
from app.db.models.datasets import VirtualDataset
from app.db.models.users import User
from app.db.session import get_db
from app.domain.mining.dynamics import compute_monthly_dynamics
from app.domain.mining.graph import build_dfg, filter_dfg
from app.domain.mining.resources import compute_resource_workload
from app.domain.mining.rework import compute_global_rework_pct, compute_rework_per_operation
from app.domain.mining.variants import get_top_n_variants, get_variants_coverage
from app.schemas.analytics import (
    CytoscapeElement,
    DFGResponse,
    MonthlyDynamicsResponse,
    MonthlyDynamicsRow,
    ResourceListResponse,
    ResourceRow,
    ReworkRow,
    ReworkTableResponse,
    TopPathsResponse,
    VariantRow,
)
from app.services import analytics_service, virtual_dataset_service

router = APIRouter(
    prefix="/projects/{project_id}/virtual-datasets/{vd_id}/analytics",
    tags=["Аналитика"],
)

ActivityLevel = Literal["raw", "role"]


async def _get_vd(db: AsyncSession, project_id: int, vd_id: int) -> VirtualDataset:
    try:
        return await virtual_dataset_service.get_virtual_dataset(db, project_id, vd_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/rework-table", response_model=ReworkTableResponse)
async def rework_table(
    project_id: int,
    vd_id: int,
    activity_level: ActivityLevel = "raw",
    limit: int = Query(default=50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ReworkTableResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(db, virtual)
    column = analytics_service.activity_column(activity_level)
    rework_df = compute_rework_per_operation(df, column)
    items = [
        ReworkRow(
            activity=str(row["activity"]),
            total=int(row["total"]),
            repeats=int(row["repeats"]),
            rework_pct=float(row["rework_pct"]),
        )
        for _, row in rework_df.head(limit).iterrows()
    ]
    return ReworkTableResponse(
        items=items,
        total_operations=int(rework_df["total"].sum()),
        total_repeats=int(rework_df["repeats"].sum()),
        global_rework_pct=compute_global_rework_pct(df, column),
    )


@router.get("/top-paths", response_model=TopPathsResponse)
async def top_paths(
    project_id: int,
    vd_id: int,
    n: int = Query(default=5, ge=1, le=50),
    activity_level: ActivityLevel = "raw",
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> TopPathsResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(db, virtual)
    column = analytics_service.activity_column(activity_level)
    variants_df = get_top_n_variants(df, n=n, activity_col=column)
    coverage = get_variants_coverage(df, n=n, activity_col=column)
    return TopPathsResponse(
        total_cases=coverage["total_cases"],
        total_variants=coverage["total_variants"],
        top_n=n,
        covered_cases=coverage["covered_cases"],
        coverage_pct=coverage["coverage_pct"],
        variants=[
            VariantRow(
                trace=list(row["trace"]),
                n_cases=int(row["n_cases"]),
                avg_duration_seconds=float(row["avg_duration_seconds"]),
                example_case_ids=list(row["example_case_ids"]),
            )
            for _, row in variants_df.iterrows()
        ],
    )


@router.get("/dfg", response_model=DFGResponse)
async def dfg(
    project_id: int,
    vd_id: int,
    activity_level: ActivityLevel = "raw",
    min_edge_frequency_pct: float = Query(default=0.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> DFGResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(db, virtual)
    column = analytics_service.activity_column(activity_level)
    graph = filter_dfg(build_dfg(df, column), min_edge_frequency_pct)
    return DFGResponse(
        nodes=[
            CytoscapeElement(
                data={
                    "id": node.activity,
                    "label": node.activity,
                    "count": node.count,
                    "avg_duration_sec": node.avg_own_duration_seconds,
                }
            )
            for node in graph.nodes
        ],
        edges=[
            CytoscapeElement(
                data={
                    "id": f"{edge.from_activity}->{edge.to_activity}",
                    "source": edge.from_activity,
                    "target": edge.to_activity,
                    "count": edge.count,
                    "avg_duration_sec": edge.avg_duration_seconds,
                }
            )
            for edge in graph.edges
        ],
        start_activities=graph.start_activities,
        end_activities=graph.end_activities,
    )


@router.get("/monthly-dynamics", response_model=MonthlyDynamicsResponse)
async def monthly_dynamics(
    project_id: int,
    vd_id: int,
    activity: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MonthlyDynamicsResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(db, virtual)
    dynamics_df = compute_monthly_dynamics(df, activity_filter=activity)
    return MonthlyDynamicsResponse(
        items=[
            MonthlyDynamicsRow(
                month=str(row["month"]),
                n_events=int(row["n_events"]),
                n_cases=int(row["n_cases"]),
                avg_sojourn_seconds=float(row["avg_sojourn_seconds"]),
            )
            for _, row in dynamics_df.iterrows()
        ]
    )


@router.get("/resources", response_model=ResourceListResponse)
async def resources(
    project_id: int,
    vd_id: int,
    limit: int = Query(default=50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ResourceListResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(db, virtual)
    workload = compute_resource_workload(df)
    return ResourceListResponse(
        items=[
            ResourceRow(
                resource=str(row["resource"]),
                n_cases=int(row["n_cases"]),
                n_events=int(row["n_events"]),
                avg_own_duration_seconds=float(row["avg_own_duration_seconds"]),
                n_unique_activities=int(row["n_unique_activities"]),
            )
            for _, row in workload.head(limit).iterrows()
        ]
    )
