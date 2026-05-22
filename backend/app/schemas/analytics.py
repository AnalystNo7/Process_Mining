from typing import Any

from pydantic import BaseModel


class ReworkRow(BaseModel):
    activity: str
    total: int
    repeats: int
    rework_pct: float


class ReworkTableResponse(BaseModel):
    items: list[ReworkRow]
    total_operations: int
    total_repeats: int
    global_rework_pct: float


class VariantRow(BaseModel):
    trace: list[str]
    n_cases: int
    avg_duration_seconds: float
    example_case_ids: list[str]


class TopPathsResponse(BaseModel):
    total_cases: int
    total_variants: int
    top_n: int
    covered_cases: int
    coverage_pct: float
    variants: list[VariantRow]


class CytoscapeElement(BaseModel):
    data: dict[str, Any]


class DFGResponse(BaseModel):
    nodes: list[CytoscapeElement]
    edges: list[CytoscapeElement]
    start_activities: dict[str, int]
    end_activities: dict[str, int]


class PathRow(BaseModel):
    index: int
    trace: list[str]
    n_cases: int
    avg_duration_seconds: float
    case_ids: list[str]


class ProcessMapResponse(BaseModel):
    mode: str
    nodes: list[CytoscapeElement]
    edges: list[CytoscapeElement]
    start_activities: dict[str, int]
    end_activities: dict[str, int]
    paths: list[PathRow]
    total_cases: int
    total_variants: int
    top_n: int
    covered_cases: int
    coverage_pct: float


class OperationSummaryRow(BaseModel):
    activity: str
    n_cases: int
    n_events: int
    avg_own_duration_seconds: float
    median_own_duration_seconds: float
    avg_share_pct: float


class OperationsResponse(BaseModel):
    items: list[OperationSummaryRow]


class FilterOptionsResponse(BaseModel):
    departments: list[str]
    roles: list[str]
    resources: list[str]
    activities: list[str]


class MonthlyDynamicsRow(BaseModel):
    month: str
    n_events: int
    n_cases: int
    avg_sojourn_seconds: float


class MonthlyDynamicsResponse(BaseModel):
    items: list[MonthlyDynamicsRow]


class ResourceRow(BaseModel):
    resource: str
    n_cases: int
    n_events: int
    avg_own_duration_seconds: float
    n_unique_activities: int


class ResourceListResponse(BaseModel):
    items: list[ResourceRow]
