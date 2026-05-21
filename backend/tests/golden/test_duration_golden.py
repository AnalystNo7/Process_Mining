import pytest

from app.domain.mining.duration import compute_sojourn_time


def test_sojourn_top10_operations(synthetic_log, expected_metrics) -> None:
    """Sojourn time для топ-10 операций совпадает с эталоном (±2%)."""
    df_sojourn = compute_sojourn_time(synthetic_log)
    expected = expected_metrics["sojourn_time_top10_operations"]

    for op_name, metrics in expected.items():
        op_data = df_sojourn[df_sojourn["activity"] == op_name]["sojourn_seconds"]
        assert len(op_data) > 0, f"операция {op_name!r} не найдена"
        assert op_data.mean() == pytest.approx(metrics["avg_sec"], rel=0.02)
        assert op_data.median() == pytest.approx(metrics["median_sec"], rel=0.02)
