from app.domain.mining.loading import deduplicate


def test_load_synthetic_log_row_counts(synthetic_log, expected_metrics) -> None:
    exp = expected_metrics["basic_kpi"]
    assert len(synthetic_log) == exp["total_events"]
    assert synthetic_log["case_id"].nunique() == exp["total_cases"]
    assert synthetic_log["activity"].nunique() == exp["unique_activities"]


def test_load_synthetic_log_timestamps_utc(synthetic_log) -> None:
    assert str(synthetic_log["timestamp_start"].dtype).endswith("UTC]")
    assert str(synthetic_log["timestamp_end"].dtype).endswith("UTC]")


def test_deduplicate_synthetic_log(synthetic_log) -> None:
    deduped, removed = deduplicate(synthetic_log)
    assert removed == 536
    assert len(deduped) == len(synthetic_log) - 536
