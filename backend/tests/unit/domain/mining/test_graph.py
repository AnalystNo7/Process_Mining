from datetime import datetime, timedelta, timezone

import pandas as pd

from app.domain.mining.graph import build_dfg, filter_dfg

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
