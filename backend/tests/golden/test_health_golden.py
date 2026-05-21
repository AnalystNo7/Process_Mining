from app.domain.mining.health import health_check


def test_health_synthetic_log_is_good(synthetic_log) -> None:
    """На эталонном логе (1328 кейсов, ~19 операций/кейс, rework ~20%,
    поля department/resource замаплены) все 5 проверок проходят."""
    report = health_check(synthetic_log)
    assert report.status == "good"
    assert {c.name for c in report.checks} == {
        "cases_count",
        "events_per_case",
        "rework_pct",
        "department_field",
        "resource_field",
    }
    assert all(c.severity == "info" for c in report.checks)
