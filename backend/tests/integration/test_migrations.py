import app.db.models  # noqa: F401 — регистрирует все модели в Base.metadata
from app.db.base import Base

EXPECTED_TABLES = {
    "auth.users",
    "auth.refresh_tokens",
    "auth.audit_log",
    "core.projects",
    "core.physical_datasets",
    "core.role_mappings",
    "core.sla_rules",
    "core.virtual_datasets",
    "core.named_slices",
    "core.dashboards",
    "core.dashboard_widgets",
    "core.annotations",
    "core.upload_templates",
    "core.global_role_templates",
    "events.event_log",
}


def test_all_tables_registered() -> None:
    """Все таблицы из 01_DATA_MODEL.md зарегистрированы в метаданных."""
    actual = {f"{t.schema}.{t.name}" for t in Base.metadata.tables.values()}
    assert EXPECTED_TABLES <= actual


def test_no_unexpected_tables() -> None:
    """В метаданных нет лишних таблиц сверх описанных в ТЗ."""
    actual = {f"{t.schema}.{t.name}" for t in Base.metadata.tables.values()}
    assert actual == EXPECTED_TABLES
