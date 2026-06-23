"""remove duplicated process widgets

Revision ID: 011
Revises: 010
Create Date: 2026-06-23 17:00:00

T47 (Фаза 6). Подвкладка `process.process` теперь рендерится богатым
компонентом `ProcessGraphTab` (embedded) — он уже содержит граф процесса,
панель путей, частотный фильтр, таблицу операций и динамику. Поэтому
из всех `standard_pm`-дашбордов удаляются дублирующие виджеты:
- `process_graph` на process.process (заменён ProcessGraphTab);
- `operations_dynamics` + `operations_summary_short` на process.duration;
- `top_paths_graph` на process.paths.

Виджеты, добавленные пользователями вручную, остаются (фильтр по
widget_type конкретный — только дефолтные T43 типы).

Подвкладка process.duration и process.paths становятся пустыми (Empty) —
пользователь может добавить свои виджеты через UI.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (tab, widget_type) — комбинации виджетов T43, которые удаляются.
_DUPLICATES = (
    ("process.process", "process_graph"),
    ("process.duration", "operations_dynamics"),
    ("process.duration", "operations_summary_short"),
    ("process.paths", "top_paths_graph"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for tab, widget_type in _DUPLICATES:
        bind.execute(
            sa.text(
                "DELETE FROM core.dashboard_widgets "
                "WHERE tab = :tab AND widget_type = :wt"
            ).bindparams(tab=tab, wt=widget_type)
        )


def downgrade() -> None:
    """Восстанавливает виджеты T43 (best-effort). Координаты и config —
    дефолтные значения с момента T43.1. Идемпотентно (WHERE NOT EXISTS):
    не дублирует, если виджет уже есть."""
    bind = op.get_bind()
    dashboard_ids = bind.execute(
        sa.text(
            "SELECT id FROM core.dashboards WHERE template_kind = 'standard_pm'"
        )
    ).scalars().all()

    # (tab, widget_type, title, config, gx, gy, gw, gh)
    defaults: list[tuple[str, str, str, str, int, int, int, int]] = [
        ("process.process", "process_graph", "Граф процесса",
         '{"max_nodes": 60, "min_edge_frequency_pct": 5.0}', 0, 0, 12, 10),
        ("process.duration", "operations_dynamics", "Динамика количества операций",
         "{}", 0, 0, 12, 5),
        ("process.duration", "operations_summary_short", "Метрики операций",
         '{"activity_level": "raw", "limit": 50}', 0, 5, 12, 7),
        ("process.paths", "top_paths_graph", "Топ-N маршрутов",
         "{}", 0, 0, 12, 10),
    ]
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
        for tab, wt, title, config, gx, gy, gw, gh in defaults:
            bind.execute(
                insert_sql.bindparams(
                    dashboard_id=dashboard_id,
                    widget_type=wt,
                    title=title,
                    config=config,
                    tab=tab,
                    grid_x=gx,
                    grid_y=gy,
                    grid_width=gw,
                    grid_height=gh,
                )
            )
