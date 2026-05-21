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
