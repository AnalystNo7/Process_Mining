import pytest

from app.domain.mining import variants


def test_unique_traces(synthetic_log, expected_metrics) -> None:
    exp = expected_metrics["process_metrics"]
    assert variants.get_case_traces(synthetic_log).nunique() == exp["unique_traces"]


def test_variability_pct(synthetic_log, expected_metrics) -> None:
    exp = expected_metrics["process_metrics"]
    actual = variants.compute_variability_pct(synthetic_log)
    assert actual == pytest.approx(exp["variability_pct"], abs=0.05)


def test_mean_occurrence_pct(synthetic_log, expected_metrics) -> None:
    exp = expected_metrics["process_metrics"]
    actual = variants.compute_mean_occurrence_pct(synthetic_log)
    assert actual == pytest.approx(exp["mean_occurrence_pct"], abs=0.05)


def test_top5_variants_coverage(synthetic_log, expected_metrics) -> None:
    coverage = variants.get_variants_coverage(synthetic_log, n=5)
    assert coverage["total_cases"] == expected_metrics["basic_kpi"]["total_cases"]
    assert coverage["total_variants"] == expected_metrics["process_metrics"]["unique_traces"]
