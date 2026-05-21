import pytest

from app.domain.mining import rework


def test_global_rework_pct(synthetic_log, expected_metrics) -> None:
    exp = expected_metrics["rework_global"]
    actual = rework.compute_global_rework_pct(synthetic_log)
    assert actual == pytest.approx(exp["global_rework_pct"], rel=0.01)


def test_duration_comparison(synthetic_log, expected_metrics) -> None:
    exp = expected_metrics["case_duration"]
    actual = rework.compute_duration_comparison(synthetic_log)
    assert actual["n_cases_with_rework"] == exp["n_cases_with_rework"]
    assert actual["n_cases_without_rework"] == exp["n_cases_without_rework"]
    assert actual["avg_duration_with_rework_seconds"] == pytest.approx(
        exp["avg_with_rework_seconds"], rel=0.01
    )
    assert actual["avg_duration_without_rework_seconds"] == pytest.approx(
        exp["avg_without_rework_seconds"], rel=0.01
    )


def test_rework_table_top10(synthetic_log, expected_metrics) -> None:
    expected_top10 = expected_metrics["top10_operations_by_volume"]
    actual = rework.compute_rework_per_operation(synthetic_log).head(10).to_dict("records")

    for exp_row, act_row in zip(expected_top10, actual, strict=True):
        assert act_row["activity"] == exp_row["operation"]
        assert act_row["total"] == exp_row["total"]
        assert act_row["repeats"] == exp_row["repeats"]
        assert act_row["rework_pct"] == pytest.approx(exp_row["rework_pct"], abs=0.05)
