"""operation durations boxplot widget

Revision ID: 012
Revises: 011
Create Date: 2026-06-26 12:00:00

T45. Добавляет виджет «Длительность операций (ящик с усами)» на подвкладку
`process.duration` всем существующим `standard_pm`-дашбордам. Раньше эта
подвкладка была пустой (см. миграцию 011: дубли с ProcessGraphTab удалены).

Идемпотентность: INSERT … WHERE NOT EXISTS — пользовательский виджет того же
типа на той же подвкладке не дублируется.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_WIDGET = {
    "widget_type": "operation_durations_boxplot",
    "title": "Длительность операций (ящик с усами)",
    "tab": "process.duration",
    "config": '{"limit": 15, "activity_level": "raw"}',
    "grid_x": 0,
    "grid_y": 0,
    "grid_width": 12,
    "grid_height": 6,
}


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
        bind.execute(insert_sql.bindparams(dashboard_id=dashboard_id, **_WIDGET))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM core.dashboard_widgets "
            "WHERE tab = 'process.duration' "
            "AND widget_type = 'operation_durations_boxplot'"
        )
    )
