from datetime import datetime, timedelta, timezone

import pandas as pd

from app.domain.mining.graph import (
    DFG,
    END_NODE,
    START_NODE,
    DFGEdge,
    DFGNode,
    build_dfg,
    build_top_paths_graph,
    filter_dfg,
    limit_dfg,
)

_EMPTY = pd.DataFrame(
    columns=["case_id", "activity", "timestamp_start", "timestamp_end"]
)


def _variants(rows: list[tuple[tuple[str, ...], int]]) -> pd.DataFrame:
    return pd.DataFrame([{"trace": trace, "n_cases": n} for trace, n in rows])

_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _ev(case: str, activity: str, hour: int) -> dict:
    return {
        "case_id": case,
        "activity": activity,
        "timestamp_start": _BASE + timedelta(hours=hour),
        "timestamp_end": _BASE + timedelta(hours=hour, minutes=30),
    }


def test_dfg_simple_chain() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C1", "B", 1), _ev("C1", "C", 2)])
    dfg = build_dfg(df)
    assert {(e.from_activity, e.to_activity) for e in dfg.edges} == {("A", "B"), ("B", "C")}
    assert dfg.start_activities == {"A": 1}
    assert dfg.end_activities == {"C": 1}


def test_dfg_self_loop() -> None:
    df = pd.DataFrame([_ev("C1", "A", 0), _ev("C1", "A", 1)])
    dfg = build_dfg(df)
    assert any(e.from_activity == "A" and e.to_activity == "A" for e in dfg.edges)


def test_dfg_nodes_have_counts() -> None:
    df = pd.DataFrame(
        [_ev("C1", "A", 0), _ev("C1", "B", 1), _ev("C2", "A", 0)]
    )
    dfg = build_dfg(df)
    node_a = next(n for n in dfg.nodes if n.activity == "A")
    assert node_a.count == 2


def test_filter_dfg_min_frequency() -> None:
    rows: list[dict] = []
    for i in range(10):
        rows += [_ev(f"C{i}", "A", 0), _ev(f"C{i}", "B", 1)]  # A→B ×10
    rows += [_ev("CX", "A", 0), _ev("CX", "C", 1)]  # A→C ×1
    dfg = filter_dfg(build_dfg(pd.DataFrame(rows)), min_edge_frequency_pct=50)
    edges = {(e.from_activity, e.to_activity) for e in dfg.edges}
    assert ("A", "B") in edges
    assert ("A", "C") not in edges


def test_build_dfg_empty() -> None:
    df = pd.DataFrame(
        columns=["case_id", "activity", "timestamp_start", "timestamp_end"]
    )
    dfg = build_dfg(df)
    assert dfg.nodes == []
    assert dfg.edges == []


def test_limit_dfg_keeps_top_nodes_and_consistent_edges() -> None:
    dfg = DFG(
        nodes=[DFGNode(f"A{i}", 100 - i, 1.0) for i in range(10)],
        edges=[
            DFGEdge("A0", "A1", 5, 1.0),
            DFGEdge("A1", "A9", 5, 1.0),
            DFGEdge("A0", "A2", 5, 1.0),
        ],
        start_activities={"A0": 5, "A9": 1},
        end_activities={"A9": 5},
    )
    limited = limit_dfg(dfg, 3)
    assert {n.activity for n in limited.nodes} == {"A0", "A1", "A2"}
    # Рёбра в недоступные узлы (A9) отброшены — иначе граф не отрисуется.
    assert {(e.from_activity, e.to_activity) for e in limited.edges} == {
        ("A0", "A1"),
        ("A0", "A2"),
    }
    assert limited.start_activities == {"A0": 5}
    assert limited.end_activities == {}


def test_limit_dfg_noop_when_within_limit() -> None:
    dfg = build_dfg(
        pd.DataFrame([_ev("C1", "A", 0), _ev("C1", "B", 1)])
    )
    assert limit_dfg(dfg, 60) is dfg


def test_top_paths_graph_merges_variant_counts() -> None:
    graph = build_top_paths_graph(
        _EMPTY, _variants([(("A", "B", "C"), 3), (("A", "C"), 2)])
    )
    counts = {n.activity: n.count for n in graph.nodes}
    assert counts["A"] == 5  # операция есть в обеих трассах
    assert counts["B"] == 3
    assert counts["C"] == 5
    assert counts[START_NODE] == 5
    assert counts[END_NODE] == 5


def test_top_paths_graph_single_edge_per_pair() -> None:
    # A→B встречается в двух разных трассах — должно остаться одно ребро.
    graph = build_top_paths_graph(
        _EMPTY, _variants([(("A", "B", "C"), 3), (("X", "A", "B"), 2)])
    )
    ab = [e for e in graph.edges if e.from_activity == "A" and e.to_activity == "B"]
    assert len(ab) == 1
    assert ab[0].count == 5


def test_top_paths_graph_synthetic_nodes_and_kind() -> None:
    graph = build_top_paths_graph(_EMPTY, _variants([(("A", "B"), 4)]))
    kinds = {n.activity: n.kind for n in graph.nodes}
    assert kinds[START_NODE] == "start"
    assert kinds[END_NODE] == "end"
    assert kinds["A"] == "operation"
    edge_pairs = {(e.from_activity, e.to_activity) for e in graph.edges}
    assert (START_NODE, "A") in edge_pairs
    assert ("B", END_NODE) in edge_pairs


def test_top_paths_graph_loop() -> None:
    # Возврат A→B→A: операция A учитывается один раз на вариант (set), но
    # рёбра A→B и B→A должны присутствовать оба.
    graph = build_top_paths_graph(_EMPTY, _variants([(("A", "B", "A"), 2)]))
    node_a = next(n for n in graph.nodes if n.activity == "A")
    assert node_a.count == 2
    edge_pairs = {(e.from_activity, e.to_activity) for e in graph.edges}
    assert ("A", "B") in edge_pairs
    assert ("B", "A") in edge_pairs


def test_top_paths_graph_empty() -> None:
    graph = build_top_paths_graph(_EMPTY, pd.DataFrame(columns=["trace", "n_cases"]))
    assert graph.nodes == []
    assert graph.edges == []
