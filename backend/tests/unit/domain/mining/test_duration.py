from datetime import datetime, timezone

import pandas as pd

from app.domain.mining.duration import (
    compute_case_duration,
    compute_case_duration_cdf,
    compute_duration_bottleneck_heatmap,
    compute_operation_durations_boxplot,
    compute_own_duration,
    compute_sojourn_time,
    compute_sojourn_vs_own,
)


def _ts(day: int, hour: int) -> datetime:
    return datetime(2025, 1, day, hour, 0, tzinfo=timezone.utc)


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_own_duration() -> None:
    df = _df(
        [{"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
          "timestamp_end": _ts(1, 12)}]
    )
    assert compute_own_duration(df).iloc[0] == 2 * 3600


def test_sojourn_first_event_equals_own_duration() -> None:
    df = _df(
        [{"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
          "timestamp_end": _ts(1, 12)}]
    )
    result = compute_sojourn_time(df)
    assert result["sojourn_seconds"].iloc[0] == 2 * 3600


def test_sojourn_subsequent_event_from_prev_end() -> None:
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 12)},
            {"case_id": "C1", "activity": "B", "timestamp_start": _ts(1, 13),
             "timestamp_end": _ts(1, 15)},
        ]
    )
    result = compute_sojourn_time(df)
    # Второе событие: 15:00 - 12:00 (конец предыдущего) = 3ч.
    second = result[result["activity"] == "B"].iloc[0]
    assert second["sojourn_seconds"] == 3 * 3600


def test_sojourn_independent_per_case() -> None:
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 11)},
            {"case_id": "C2", "activity": "A", "timestamp_start": _ts(1, 14),
             "timestamp_end": _ts(1, 16)},
        ]
    )
    result = compute_sojourn_time(df)
    # Оба — первые в своих кейсах → собственная длительность.
    assert set(result["sojourn_seconds"]) == {3600, 7200}


def test_case_duration() -> None:
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 12)},
            {"case_id": "C1", "activity": "B", "timestamp_start": _ts(2, 10),
             "timestamp_end": _ts(2, 14)},
        ]
    )
    result = compute_case_duration(df)
    row = result.iloc[0]
    assert row["n_events"] == 2
    # с 1 янв 10:00 по 2 янв 14:00 = 28ч.
    assert row["duration_seconds"] == 28 * 3600


# T45: «ящик с усами» — распределение длительности по операциям.


def test_boxplot_empty_df_returns_empty_traces() -> None:
    assert compute_operation_durations_boxplot(pd.DataFrame()) == {"traces": []}


def test_boxplot_missing_duration_column_returns_empty_traces() -> None:
    df = _df([{"activity": "A"}])
    assert compute_operation_durations_boxplot(df) == {"traces": []}


def test_boxplot_groups_by_activity_and_computes_quartiles() -> None:
    df = _df(
        [{"activity": "A", "own_duration_sec": v} for v in [10, 20, 30, 40, 50]]
        + [{"activity": "B", "own_duration_sec": v} for v in [1, 2, 3]]
    )
    result = compute_operation_durations_boxplot(df)
    by_name = {t["name"]: t for t in result["traces"]}
    assert set(by_name) == {"A", "B"}
    # A: n=5, median=30, mean=30, min=10, max=50, q1=20, q3=40 (linear).
    a = by_name["A"]
    assert a["n"] == 5
    assert a["median"] == 30.0
    assert a["mean"] == 30.0
    assert a["min"] == 10.0
    assert a["max"] == 50.0
    assert a["q1"] == 20.0
    assert a["q3"] == 40.0
    assert a["y"] == [10.0, 20.0, 30.0, 40.0, 50.0]


def test_boxplot_sorts_by_count_descending_and_applies_limit() -> None:
    # A — 5 событий, B — 3, C — 1. limit=2 → останутся A и B, без C.
    df = _df(
        [{"activity": "A", "own_duration_sec": v} for v in range(5)]
        + [{"activity": "B", "own_duration_sec": v} for v in range(3)]
        + [{"activity": "C", "own_duration_sec": 42}]
    )
    result = compute_operation_durations_boxplot(df, limit=2)
    names = [t["name"] for t in result["traces"]]
    assert names == ["A", "B"]


def test_boxplot_single_event_does_not_crash() -> None:
    df = _df([{"activity": "A", "own_duration_sec": 123.0}])
    [trace] = compute_operation_durations_boxplot(df)["traces"]
    assert trace["n"] == 1
    assert trace["median"] == 123.0
    assert trace["q1"] == trace["q3"] == 123.0


def test_boxplot_drops_null_durations() -> None:
    df = pd.DataFrame(
        {"activity": ["A", "A", "A"], "own_duration_sec": [10.0, None, 30.0]}
    )
    [trace] = compute_operation_durations_boxplot(df)["traces"]
    assert trace["n"] == 2
    assert trace["y"] == [10.0, 30.0]


# Комбо-длительность №1: CDF длительности кейсов.


def _cases_df(durations_hours: list[int]) -> pd.DataFrame:
    """По кейсу на каждую длительность: одно событие start→end на N часов."""
    rows = []
    for i, h in enumerate(durations_hours):
        rows.append(
            {"case_id": f"C{i}", "activity": "A",
             "timestamp_start": _ts(1, 0), "timestamp_end": _ts(1 + h // 24, h % 24)}
        )
    return _df(rows)


def test_cdf_empty_df() -> None:
    result = compute_case_duration_cdf(pd.DataFrame())
    assert result["points"] == []
    assert result["percentiles"] is None


def test_cdf_monotonic_and_reaches_100() -> None:
    df = _cases_df([1, 2, 3, 4])
    result = compute_case_duration_cdf(df)
    ys = [p["y"] for p in result["points"]]
    assert ys == sorted(ys), "y должна быть неубывающей"
    assert ys[-1] == 100.0
    xs = [p["x"] for p in result["points"]]
    assert xs == sorted(xs), "x должна идти по возрастанию длительности"


def test_cdf_pct_within_sla() -> None:
    # Длительности 1ч, 2ч, 3ч, 4ч; цель 2ч → 2 из 4 = 50%.
    df = _cases_df([1, 2, 3, 4])
    result = compute_case_duration_cdf(df, sla_target_seconds=2 * 3600)
    assert result["pct_within_sla"] == 50.0
    assert result["sla_target_seconds"] == 2 * 3600


def test_cdf_no_sla_target_means_none() -> None:
    df = _cases_df([1, 2])
    result = compute_case_duration_cdf(df)
    assert result["pct_within_sla"] is None
    assert result["sla_target_seconds"] is None


# Комбо-длительность №2: теплокарта узких мест.


def test_bottleneck_heatmap_empty() -> None:
    assert compute_duration_bottleneck_heatmap(pd.DataFrame())["cells"] == []


def test_bottleneck_heatmap_median_per_cell() -> None:
    df = _df(
        [
            {"activity": "A", "department": "D1", "own_duration_sec": 10.0},
            {"activity": "A", "department": "D1", "own_duration_sec": 30.0},
            {"activity": "A", "department": "D2", "own_duration_sec": 100.0},
            {"activity": "B", "department": "D1", "own_duration_sec": 5.0},
        ]
    )
    result = compute_duration_bottleneck_heatmap(df, dimension_col="department")
    cells = {(c["x"], c["y"]): c["value"] for c in result["cells"]}
    assert cells[("A", "D1")] == 20.0  # median(10, 30)
    assert cells[("A", "D2")] == 100.0
    assert cells[("B", "D1")] == 5.0
    assert result["y_label"] == "Департамент"


def test_bottleneck_heatmap_resource_dimension_label() -> None:
    df = _df([{"activity": "A", "resource": "U1", "own_duration_sec": 7.0}])
    result = compute_duration_bottleneck_heatmap(df, dimension_col="resource")
    assert result["y_label"] == "Исполнитель"
    assert result["cells"][0]["value"] == 7.0


# Комбо-длительность №3: работа vs ожидание.


def test_sojourn_vs_own_empty() -> None:
    assert compute_sojourn_vs_own(pd.DataFrame())["rows"] == []


def test_sojourn_vs_own_first_event_has_zero_wait() -> None:
    # Один кейс, одно событие → sojourn == own → ожидание = 0.
    df = _df(
        [{"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
          "timestamp_end": _ts(1, 12)}]
    )
    df["own_duration_sec"] = compute_own_duration(df)
    [row] = compute_sojourn_vs_own(df)["rows"]
    assert row["work_seconds"] == 2 * 3600
    assert row["wait_seconds"] == 0.0


def test_sojourn_vs_own_wait_is_sojourn_minus_own() -> None:
    # Второе событие: работа 2ч (13→15), ожидание = sojourn(15-12=3ч) - own(2ч) = 1ч.
    df = _df(
        [
            {"case_id": "C1", "activity": "A", "timestamp_start": _ts(1, 10),
             "timestamp_end": _ts(1, 12)},
            {"case_id": "C1", "activity": "B", "timestamp_start": _ts(1, 13),
             "timestamp_end": _ts(1, 15)},
        ]
    )
    df["own_duration_sec"] = compute_own_duration(df)
    rows = {r["activity"]: r for r in compute_sojourn_vs_own(df)["rows"]}
    assert rows["B"]["work_seconds"] == 2 * 3600
    assert rows["B"]["wait_seconds"] == 1 * 3600
