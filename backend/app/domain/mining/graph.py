"""Directly-Follows Graph — граф непосредственного следования (02_DOMAIN_LOGIC.md)."""

from dataclasses import dataclass, field

import pandas as pd

from app.domain.mining.duration import compute_own_duration

START_NODE = "__start__"
END_NODE = "__end__"


@dataclass
class DFGNode:
    activity: str
    count: int
    avg_own_duration_seconds: float
    kind: str = "operation"  # operation | start | end


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


def _avg_own_duration_by_activity(
    df: pd.DataFrame, activity_col: str
) -> dict[str, float]:
    if len(df) == 0 or activity_col not in df.columns:
        return {}
    own = compute_own_duration(df)
    means = own.groupby(df[activity_col]).mean()
    return {str(k): _safe_float(v) for k, v in means.to_dict().items()}


def build_top_paths_graph(
    df: pd.DataFrame,
    variants_df: pd.DataFrame,
    activity_col: str = "activity",
) -> DFG:
    """Граф топ-N путей: объединение трасс из ``variants_df``.

    Узел-операция: count = число ВХОЖДЕНИЙ операции (событий) во всех кейсах
    топ-N путей — повтор операции в трассе считается каждый раз. Одно ребро на
    пару (from, to): count = число вхождений перехода. Добавляет синтетические
    узлы ``__start__``/``__end__`` (kind = start/end) и рёбра к ним."""
    if len(variants_df) == 0:
        return DFG()

    node_counts: dict[str, int] = {}
    edge_counts: dict[tuple[str, str], int] = {}
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    covered = 0

    for _, row in variants_df.iterrows():
        trace = tuple(row["trace"])
        if not trace:
            continue
        n_cases = int(row["n_cases"])
        covered += n_cases
        for activity in trace:
            node_counts[activity] = node_counts.get(activity, 0) + n_cases
        starts[trace[0]] = starts.get(trace[0], 0) + n_cases
        ends[trace[-1]] = ends.get(trace[-1], 0) + n_cases
        pairs = [(START_NODE, trace[0]), *zip(trace, trace[1:]), (trace[-1], END_NODE)]
        for pair in pairs:
            edge_counts[pair] = edge_counts.get(pair, 0) + n_cases

    own_dur = _avg_own_duration_by_activity(df, activity_col)
    nodes = [
        DFGNode(START_NODE, covered, 0.0, kind="start"),
        DFGNode(END_NODE, covered, 0.0, kind="end"),
        *(
            DFGNode(activity, count, own_dur.get(activity, 0.0))
            for activity, count in node_counts.items()
        ),
    ]
    edges = [
        DFGEdge(from_act, to_act, count, 0.0)
        for (from_act, to_act), count in edge_counts.items()
    ]
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


def limit_dfg(dfg: DFG, max_nodes: int) -> DFG:
    """Оставляет только max_nodes самых частых узлов и рёбра между ними.

    Нужен для отрисовки: граф из сотен операций не читается и тормозит UI."""
    if max_nodes <= 0 or len(dfg.nodes) <= max_nodes:
        return dfg
    top_nodes = sorted(dfg.nodes, key=lambda n: n.count, reverse=True)[:max_nodes]
    kept = {node.activity for node in top_nodes}
    return DFG(
        nodes=top_nodes,
        edges=[
            edge
            for edge in dfg.edges
            if edge.from_activity in kept and edge.to_activity in kept
        ],
        start_activities={
            k: v for k, v in dfg.start_activities.items() if k in kept
        },
        end_activities={k: v for k, v in dfg.end_activities.items() if k in kept},
    )
