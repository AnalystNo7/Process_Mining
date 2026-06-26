"""duration combo widgets

Revision ID: 013
Revises: 012
Create Date: 2026-06-26 14:00:00

Комбо-длительность. Добавляет три виджета на подвкладку `process.duration`
всем существующим `standard_pm`-дашбордам (рядом с боксплотом из T45):
- case_duration_cdf — кривая длительности кейсов (CDF) с линией SLA;
- duration_bottleneck_heatmap — теплокарта узких мест (операция × департамент,
  медиана длительности);
- sojourn_vs_own — работа vs ожидание по операциям.

Идемпотентность: INSERT … WHERE NOT EXISTS — не дублирует, если виджет того же
типа на этой подвкладке уже есть.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (widget_type, title, config, grid_x, grid_y, grid_width, grid_height)
_WIDGETS = [
    ("case_duration_cdf", "Кривая длительности кейсов (SLA)",
     '{"sla_target_hours": 24}', 0, 6, 12, 6),
    ("duration_bottleneck_heatmap", "Узкие места: длительность по операциям",
     '{"dimension": "department", "activity_level": "raw"}', 0, 12, 12, 7),
    ("sojourn_vs_own", "Работа и ожидание по операциям",
     '{"limit": 15, "activity_level": "raw"}', 0, 19, 12, 6),
]
_TAB = "process.duration"


def upgrade() -> None:
    bind = op.get_bind()
    dashboard_ids = bind.execute(
        sa.text(
            "SELECT id FROM core.dashboards WHERE template_kind = 'standard_pm'"
        )
    ).scalars().all()

    insert_sql = sa.text(
        """
        INSERT INTO core.dashboard_widgets
            (dashboard_id, widget_type, title, config, tab, use_global_filters,
             grid_x, grid_y, grid_width, grid_height)
        SELECT :dashboard_id, :widget_type, :title, CAST(:config AS jsonb),
               :tab, true, :grid_x, :grid_y, :grid_width, :grid_height
        WHERE NOT EXISTS (
            SELECT 1 FROM core.dashboard_widgets
            WHERE dashboard_id = :dashboard_id
              AND tab = :tab
              AND widget_type = :widget_type
        )
        """
    )
    for dashboard_id in dashboard_ids:
        for wt, title, config, gx, gy, gw, gh in _WIDGETS:
            bind.execute(
                insert_sql.bindparams(
                    dashboard_id=dashboard_id,
                    widget_type=wt,
                    title=title,
                    config=config,
                    tab=_TAB,
                    grid_x=gx,
                    grid_y=gy,
                    grid_width=gw,
                    grid_height=gh,
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM core.dashboard_widgets "
            "WHERE tab = :tab AND widget_type IN "
            "('case_duration_cdf', 'duration_bottleneck_heatmap', 'sojourn_vs_own')"
        ).bindparams(tab=_TAB)
    )
