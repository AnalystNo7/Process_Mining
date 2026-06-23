"""process subtabs defaults

Revision ID: 008
Revises: 007
Create Date: 2026-06-23 14:00:00

T43 (Фаза 6). Наполняет подвкладки «Процесс» дефолтными виджетами в каждом
существующем `standard_pm`-дашборде:
- process.process       — process_graph (DFG)
- process.duration      — operations_dynamics + operations_summary_short
- process.rework        — rework_table
- process.paths         — top_paths_graph
- process.distribution  — monthly_dynamics

Идемпотентность: каждый виджет вставляется только если на этой подвкладке
такого widget_type ещё нет (NOT EXISTS-pattern). Это критично, чтобы:
1) не дублировать operations_dynamics на process.duration (был с T41);
2) не перезаписать ручные виджеты пользователей, добавленные через UI.

Синхронизировано с `app/services/dashboard_service.py::_PROCESS_WIDGETS`.
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (tab, widget_type, title, config, grid_x, grid_y, grid_width, grid_height)
_DEFAULTS: list[tuple[str, str, str, dict, int, int, int, int]] = [
    ("process.process", "process_graph", "Граф процесса", {}, 0, 0, 12, 10),
    ("process.duration", "operations_dynamics", "Динамика количества операций",
     {}, 0, 0, 12, 5),
    ("process.duration", "operations_summary_short", "Метрики операций",
     {"activity_level": "raw", "limit": 50}, 0, 5, 12, 7),
    ("process.rework", "rework_table", "Таблица переделок", {}, 0, 0, 12, 8),
    ("process.paths", "top_paths_graph", "Топ-N маршрутов", {}, 0, 0, 12, 10),
    ("process.distribution", "monthly_dynamics", "Динамика по месяцам",
     {}, 0, 0, 12, 10),
]

_PROCESS_TABS = (
    "process.process",
    "process.rework",
    "process.paths",
    "process.distribution",
)


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
        for tab, wt, title, config, gx, gy, gw, gh in _DEFAULTS:
            bind.execute(
                insert_sql.bindparams(
                    dashboard_id=dashboard_id,
                    widget_type=wt,
                    title=title,
                    config=json.dumps(config),
                    tab=tab,
                    grid_x=gx,
                    grid_y=gy,
                    grid_width=gw,
                    grid_height=gh,
                )
            )


def downgrade() -> None:
    # Удаляем только виджеты подвкладок, которые до T43 были полностью пустыми.
    # process.duration не трогаем — там operations_dynamics стоял ещё с T41.
    op.execute(
        sa.text(
            "DELETE FROM core.dashboard_widgets WHERE tab = ANY(:tabs)"
        ).bindparams(tabs=list(_PROCESS_TABS))
    )
    # А на process.duration убираем только operations_summary_short (его
    # добавил T43); operations_dynamics — нет, он был с T41.
    op.execute(
        "DELETE FROM core.dashboard_widgets "
        "WHERE tab = 'process.duration' "
        "  AND widget_type = 'operations_summary_short' "
        "  AND title = 'Метрики операций'"
    )
