from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import EntityNotFoundError
from app.db.models.users import User
from app.db.session import get_db
from app.domain.mining.rework import compute_global_rework_pct, compute_rework_per_operation
from app.domain.mining.variants import get_top_n_variants, get_variants_coverage
from app.schemas.analytics import (
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


@router.get("/rework-table", response_model=ReworkTableResponse)
async def rework_table(
    project_id: int,
    vd_id: int,
    activity_level: ActivityLevel = "raw",
    limit: int = Query(default=50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ReworkTableResponse:
    try:
        virtual = await virtual_dataset_service.get_virtual_dataset(db, project_id, vd_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

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
    try:
        virtual = await virtual_dataset_service.get_virtual_dataset(db, project_id, vd_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

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
