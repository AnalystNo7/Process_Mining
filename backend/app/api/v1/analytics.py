from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import EntityNotFoundError
from app.db.models.datasets import VirtualDataset
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.session import get_db
from app.domain.mining.bpmn_export import dfg_to_bpmn
from app.domain.mining.dynamics import compute_monthly_dynamics
from app.domain.mining.graph import build_dfg, filter_dfg
from app.domain.mining.resources import compute_resource_workload
from app.domain.mining.rework import compute_global_rework_pct, compute_rework_per_operation
from app.domain.mining.sla import aggregate_sla_compliance, evaluate_sla
from app.domain.mining.variants import get_top_n_variants, get_variants_coverage
from app.domain.mining.workday import WorkdayCalculator
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
from app.schemas.cases import (
    CaseDetailResponse,
    CaseEvent,
    CaseListResponse,
    CaseSummary,
)
from app.schemas.sla import SLAComplianceResponse, SLAComplianceRow
from app.services import analytics_service, case_service, virtual_dataset_service

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
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ReworkTableResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
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
        total_operations=int(rework_df["total"].sum()) if len(rework_df) else 0,
        total_repeats=int(rework_df["repeats"].sum()) if len(rework_df) else 0,
        global_rework_pct=compute_global_rework_pct(df, column),
    )


@router.get("/top-paths", response_model=TopPathsResponse)
async def top_paths(
    project_id: int,
    vd_id: int,
    n: int = Query(default=5, ge=1, le=50),
    activity_level: ActivityLevel = "raw",
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> TopPathsResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
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
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> DFGResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
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


@router.get("/bpmn")
async def export_bpmn(
    project_id: int,
    vd_id: int,
    activity_level: ActivityLevel = "raw",
    min_edge_frequency_pct: float = Query(default=0.0, ge=0, le=100),
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Response:
    """Экспортирует текущий DFG-граф в BPMN 2.0 XML-файл."""
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
    column = analytics_service.activity_column(activity_level)
    graph = filter_dfg(build_dfg(df, column), min_edge_frequency_pct)
    project = await db.get(Project, virtual.project_id)
    process_name = project.name if project is not None else virtual.name
    xml = dfg_to_bpmn(graph, process_name=process_name)
    return Response(
        content=xml,
        media_type="application/bpmn+xml",
        headers={"Content-Disposition": f'attachment; filename="dfg_{vd_id}.bpmn"'},
    )


@router.get("/monthly-dynamics", response_model=MonthlyDynamicsResponse)
async def monthly_dynamics(
    project_id: int,
    vd_id: int,
    activity: str | None = None,
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MonthlyDynamicsResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
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


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    project_id: int,
    vd_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CaseListResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
    rows, total = case_service.list_cases(df, page=page, page_size=page_size)
    return CaseListResponse(
        items=[CaseSummary(**row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/case/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    project_id: int,
    vd_id: int,
    case_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> CaseDetailResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(db, virtual)
    try:
        detail = case_service.case_detail(df, case_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return CaseDetailResponse(
        case_id=detail["case_id"],
        attributes=detail["attributes"],
        events=[CaseEvent(**event) for event in detail["events"]],
        total_duration_seconds=detail["total_duration_seconds"],
        has_rework=detail["has_rework"],
        n_events=detail["n_events"],
    )


@router.get("/sla-compliance", response_model=SLAComplianceResponse)
async def sla_compliance(
    project_id: int,
    vd_id: int,
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SLAComplianceResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
    evaluated = evaluate_sla(df, virtual.sla_rules_snapshot, WorkdayCalculator())
    result = aggregate_sla_compliance(evaluated)
    return SLAComplianceResponse(
        rows=[SLAComplianceRow(**row) for row in result["rows"]],
        overall_compliance_pct=result["overall_compliance_pct"],
    )


@router.get("/resources", response_model=ResourceListResponse)
async def resources(
    project_id: int,
    vd_id: int,
    limit: int = Query(default=50, ge=1, le=1000),
    filters: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ResourceListResponse:
    virtual = await _get_vd(db, project_id, vd_id)
    df = await analytics_service.load_vd_dataframe(
        db, virtual, analytics_service.filter_from_query(filters)
    )
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
