"""overview layout v3

Revision ID: 006
Revises: 005
Create Date: 2026-06-23 12:00:00

T41.2 (Фаза 6). Растягивает «Динамику по месяцам» по высоте (h=8 → h=10) и
равномерно распределяет столбик из 4 KPI справа по новой высоте динамики
(y=2,4,6,8 → 2,5,8,11). Соответственно опускаются нижние ряды виджетов:
гистограмма/поток (y=10 → 13) и таблицы (y=15 → 18).

Применяется ко ВСЕМ `standard_pm`-дашбордам в БД. Координаты выставляются
прямыми UPDATE'ами по `(tab='overview', widget_type[, title])` — id виджетов
сохраняются (важно, если на них есть внешние ссылки). Idempotent: повторный
прогон выставит те же значения.

Синхронизировано с `app/services/dashboard_service.py::_OVERVIEW_WIDGETS`.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (title, new_y) для 4 KPI справа (x=9, w=3).
_RIGHT_KPI_NEW_Y: list[tuple[str, int]] = [
    ("Начало процесса", 2),
    ("Конец процесса", 5),
    ("Вариативность путей", 8),
    ("Встречаемость операций", 11),
]

# Для downgrade — координаты T41.1.
_RIGHT_KPI_OLD_Y: list[tuple[str, int]] = [
    ("Начало процесса", 2),
    ("Конец процесса", 4),
    ("Вариативность путей", 6),
    ("Встречаемость операций", 8),
]


def _apply_layout(
    dynamics_h: int,
    right_kpi: list[tuple[str, int]],
    middle_y: int,
    bottom_y: int,
) -> None:
    bind = op.get_bind()
    # Динамика по месяцам — изменить высоту.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET grid_height = :h "
            "WHERE tab = 'overview' AND widget_type = 'monthly_dynamics'"
        ).bindparams(h=dynamics_h)
    )
    # Столбик 4 KPI справа.
    for title, y in right_kpi:
        bind.execute(
            sa.text(
                "UPDATE core.dashboard_widgets "
                "SET grid_y = :y "
                "WHERE tab = 'overview' "
                "  AND widget_type = 'kpi_card' "
                "  AND grid_x = 9 AND grid_width = 3 "
                "  AND title = :title"
            ).bindparams(y=y, title=title)
        )
    # Средний ряд: гистограмма | поток.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET grid_y = :y "
            "WHERE tab = 'overview' "
            "  AND widget_type IN ('events_per_case_histogram', 'case_flow_cumulative')"
        ).bindparams(y=middle_y)
    )
    # Нижний ряд: повторы | пути.
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET grid_y = :y "
            "WHERE tab = 'overview' "
            "  AND widget_type IN ('rework_table', 'top_paths_graph')"
        ).bindparams(y=bottom_y)
    )


def upgrade() -> None:
    _apply_layout(
        dynamics_h=10,
        right_kpi=_RIGHT_KPI_NEW_Y,
        middle_y=13,
        bottom_y=18,
    )


def downgrade() -> None:
    _apply_layout(
        dynamics_h=8,
        right_kpi=_RIGHT_KPI_OLD_Y,
        middle_y=10,
        bottom_y=15,
    )
