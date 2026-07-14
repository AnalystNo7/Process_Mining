"""bottleneck heatmap: second view (by frequency) + readable config

Revision ID: 014
Revises: 013
Create Date: 2026-06-29 11:00:00

Улучшение теплокарты узких мест (читаемость). Для существующих
`standard_pm`-дашбордов:
1. Существующая теплокарта (из 013) переводится в «топ-10 по длительности»:
   в config добавляются sort_by='duration' и limit=10, высота 7→8, заголовок
   уточняется.
2. Добавляется вторая теплокарта «топ-10 по частоте» (sort_by='frequency').
3. Виджет «Работа и ожидание» сдвигается ниже (y=19 → 28), чтобы освободить
   место под вторую теплокарту.

Идемпотентность: апдейт первой теплокарты — только если у неё ещё нет
sort_by; вставка второй — WHERE NOT EXISTS по config sort_by='frequency'.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TAB = "process.duration"


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Существующая теплокарта → явный «топ-10 по длительности».
    bind.execute(
        sa.text(
            """
            UPDATE core.dashboard_widgets
            SET config = config || '{"sort_by": "duration", "limit": 10}'::jsonb,
                grid_height = 8,
                title = 'Узкие места: топ-10 операций по длительности'
            WHERE tab = :tab
              AND widget_type = 'duration_bottleneck_heatmap'
              AND NOT (config ? 'sort_by')
            """
        ).bindparams(tab=_TAB)
    )

    # 2) Сдвигаем «Работа и ожидание» вниз, чтобы не перекрывалась.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets SET grid_y = 28 "
            "WHERE tab = :tab AND widget_type = 'sojourn_vs_own' AND grid_y < 28"
        ).bindparams(tab=_TAB)
    )

    # 3) Вторая теплокарта — «топ-10 по частоте».
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
               '{"dimension": "department", "activity_level": "raw",'
               ' "sort_by": "frequency", "limit": 10}'::jsonb,
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


def downgrade() -> None:
    bind = op.get_bind()
    # Удаляем теплокарту «по частоте».
    bind.execute(
        sa.text(
            "DELETE FROM core.dashboard_widgets "
            "WHERE tab = :tab AND widget_type = 'duration_bottleneck_heatmap' "
            "AND config ->> 'sort_by' = 'frequency'"
        ).bindparams(tab=_TAB)
    )
    # Возвращаем sojourn на место.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets SET grid_y = 19 "
            "WHERE tab = :tab AND widget_type = 'sojourn_vs_own' AND grid_y = 28"
        ).bindparams(tab=_TAB)
    )
