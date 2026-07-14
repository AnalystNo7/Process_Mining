"""remove duplicate bottleneck heatmap (by frequency)

Revision ID: 017
Revises: 016
Create Date: 2026-07-14 12:00:00

После добавления меню «По частоте / По длительности» в шапку теплокарты вторая
карта «топ-10 по частоте» (добавлена миграцией 014) стала дублем — режим
переключается в один клик. Убираем её с существующих дашбордов и поднимаем
«Работа и ожидание» на освободившееся место. Даунгрейд возвращает карту
(идемпотентно, по образцу 014).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TAB = "process.duration"


def upgrade() -> None:
    bind = op.get_bind()
    # Удаляем теплокарту «по частоте» (матчим по config, не по заголовку).
    bind.execute(
        sa.text(
            "DELETE FROM core.dashboard_widgets "
            "WHERE tab = :tab AND widget_type = 'duration_bottleneck_heatmap' "
            "AND config ->> 'sort_by' = 'frequency'"
        ).bindparams(tab=_TAB)
    )
    # Поднимаем «Работа и ожидание» на освободившееся место.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets SET grid_y = 20 "
            "WHERE tab = :tab AND widget_type = 'sojourn_vs_own' AND grid_y = 28"
        ).bindparams(tab=_TAB)
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Возвращаем sojourn вниз, освобождая место под вторую теплокарту.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets SET grid_y = 28 "
            "WHERE tab = :tab AND widget_type = 'sojourn_vs_own' AND grid_y = 20"
        ).bindparams(tab=_TAB)
    )

    # Восстанавливаем карту «по частоте» (как в 014.upgrade, идемпотентно).
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
        SELECT :dashboard_id, 'duration_bottleneck_heatmap',
               'Узкие места: топ-10 операций по частоте',
               '{"dimension":"department","activity_level":"raw",'
               '"sort_by":"frequency","limit":10}'::jsonb,
               :tab, true, 0, 20, 12, 8
        WHERE NOT EXISTS (
            SELECT 1 FROM core.dashboard_widgets
            WHERE dashboard_id = :dashboard_id
              AND tab = :tab
              AND widget_type = 'duration_bottleneck_heatmap'
              AND config ->> 'sort_by' = 'frequency'
        )
        """
    )
    for dashboard_id in dashboard_ids:
        bind.execute(insert_sql.bindparams(dashboard_id=dashboard_id, tab=_TAB))
