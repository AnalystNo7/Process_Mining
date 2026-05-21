"""Directly-Follows Graph — граф непосредственного следования (02_DOMAIN_LOGIC.md)."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class DFGNode:
    activity: str
    count: int
    avg_own_duration_seconds: float


@dataclass
class DFGEdge:
    from_activity: str
    to_activity: str
    count: int
    avg_duration_seconds: float


@dataclass
class DFG:
    nodes: list[DFGNode] = field(default_factory=list)
    edges: list[DFGEdge] = field(default_factory=list)
    start_activities: dict[str, int] = field(default_factory=dict)
    end_activities: dict[str, int] = field(default_factory=dict)


def _safe_float(value: object) -> float:
    return 0.0 if value is None or pd.isna(value) else float(value)  # type: ignore[arg-type]


def build_dfg(df: pd.DataFrame, activity_col: str = "activity") -> DFG:
    """Строит DFG: узлы — операции, рёбра — переходы между последовательными
    операциями в кейсе. Сортировка внутри кейса по timestamp_start."""
    if len(df) == 0:
        return DFG()

    work = df.sort_values(["case_id", "timestamp_start", "timestamp_end"]).copy()
    if "own_duration_sec" not in work.columns:
        work["own_duration_sec"] = (
            work["timestamp_end"] - work["timestamp_start"]
        ).dt.total_seconds()

    work["next_activity"] = work.groupby("case_id")[activity_col].shift(-1)
    work["next_start"] = work.groupby("case_id")["timestamp_start"].shift(-1)
    work["transition_duration"] = (
        work["next_start"] - work["timestamp_end"]
    ).dt.total_seconds()

    edges_df = (
        work[work["next_activity"].notna()]
        .groupby([activity_col, "next_activity"])
        .agg(count=("case_id", "count"), avg_duration=("transition_duration", "mean"))
        .reset_index()
    )
    edges = [
        DFGEdge(
            from_activity=str(row[activity_col]),
            to_activity=str(row["next_activity"]),
            count=int(row["count"]),
            avg_duration_seconds=_safe_float(row["avg_duration"]),
        )
        for _, row in edges_df.iterrows()
    ]

    nodes_df = (
        work.groupby(activity_col)
        .agg(count=("case_id", "count"), avg_own=("own_duration_sec", "mean"))
        .reset_index()
    )
    nodes = [
        DFGNode(
            activity=str(row[activity_col]),
            count=int(row["count"]),
            avg_own_duration_seconds=_safe_float(row["avg_own"]),
        )
        for _, row in nodes_df.iterrows()
    ]

    starts = {
        str(k): int(v)
        for k, v in work.groupby("case_id")
        .first()[activity_col]
        .value_counts()
        .to_dict()
        .items()
    }
    ends = {
        str(k): int(v)
        for k, v in work.groupby("case_id")
        .last()[activity_col]
        .value_counts()
        .to_dict()
        .items()
    }
    return DFG(nodes=nodes, edges=edges, start_activities=starts, end_activities=ends)


def filter_dfg(dfg: DFG, min_edge_frequency_pct: float = 0.0) -> DFG:
    """Возвращает упрощённый граф: рёбра с count < min_edge_frequency_pct%
    от максимальной частоты удаляются."""
    if not dfg.edges or min_edge_frequency_pct <= 0:
        return dfg
    max_count = max(edge.count for edge in dfg.edges)
    threshold = max_count * min_edge_frequency_pct / 100.0
    kept_edges = [edge for edge in dfg.edges if edge.count >= threshold]
    return DFG(
        nodes=dfg.nodes,
        edges=kept_edges,
        start_activities=dfg.start_activities,
        end_activities=dfg.end_activities,
    )
