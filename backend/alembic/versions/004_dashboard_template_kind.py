"""dashboard template kind and widget tab

Revision ID: 004
Revises: 003
Create Date: 2026-06-18 12:00:00

T41 (Фаза 6). Каркас вкладочного дашборда «Стандартные / Обзор / Процесс×5 / Детали×3».

* `core.dashboards.template_kind` — `standard_pm` (новый шаблон) или `legacy`
  (резерв на случай отката). По умолчанию все новые дашборды создаются как
  `standard_pm`.
* `core.dashboard_widgets.tab` — путь вкладки: `standard_metrics`, `overview`,
  `process.process`, `process.duration`, `process.rework`, `process.paths`,
  `process.distribution`, `details.cases`, `details.operations`,
  `details.dataset`.

Принудительная миграция (раздел G плана): существующим виджетам присваиваем
`tab` по эвристике widget_type → вкладка. Это сохраняет пользовательские
кастомизации позиций, но переносит виджеты в правильные вкладки.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_WIDGET_TYPE_TO_TAB: dict[str, str] = {
    # KPI и обзорные потоки — на «Обзор»
    "kpi_card": "overview",
    "case_flow_cumulative": "overview",
    "events_per_case_histogram": "overview",
    # Динамика операций — в Процесс/Длительность
    "operations_dynamics": "process.duration",
    # Таблица операций — в Детали/Операции
    "operations_summary_short": "details.operations",
    "operations_summary": "details.operations",
}


def upgrade() -> None:
    op.add_column(
        "dashboards",
        sa.Column(
            "template_kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'standard_pm'"),
        ),
        schema="core",
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("tab", sa.String(length=50), nullable=True),
        schema="core",
    )
    # Эвристическая раскладка существующих виджетов по вкладкам.
    for widget_type, tab in _WIDGET_TYPE_TO_TAB.items():
        op.execute(
            sa.text(
                "UPDATE core.dashboard_widgets SET tab = :tab "
                "WHERE widget_type = :wt AND tab IS NULL"
            ).bindparams(tab=tab, wt=widget_type)
        )
    # Всё, что не покрылось эвристикой — на «Обзор» (дальше пользователь
    # перетащит вручную).
    op.execute(
        "UPDATE core.dashboard_widgets SET tab = 'overview' WHERE tab IS NULL"
    )
    op.alter_column(
        "dashboard_widgets",
        "tab",
        nullable=False,
        existing_type=sa.String(length=50),
        schema="core",
    )
    op.create_index(
        "idx_widgets_dashboard_tab",
        "dashboard_widgets",
        ["dashboard_id", "tab"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_widgets_dashboard_tab", table_name="dashboard_widgets", schema="core"
    )
    op.drop_column("dashboard_widgets", "tab", schema="core")
    op.drop_column("dashboards", "template_kind", schema="core")
