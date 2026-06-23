"""overview layout v4

Revision ID: 007
Revises: 006
Create Date: 2026-06-23 13:00:00

T41.3 (Фаза 6). Доводит выравнивание динамики и столбика KPI до точного:
- monthly_dynamics.grid_height: 10 → 11 (низ динамики совпадает с низом
  последнего KPI «Встречаемость операций», оба заканчиваются на строке 13);
- нижние ряды (гистограмма/поток, повторы/пути) опускаются на 1 строку.

Применяется ко ВСЕМ `standard_pm`-дашбордам через прямые UPDATE'ы по
`(tab='overview', widget_type)`. Id виджетов сохраняются. Idempotent.

Синхронизировано с `app/services/dashboard_service.py::_OVERVIEW_WIDGETS`.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _apply(dynamics_h: int, middle_y: int, bottom_y: int) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET grid_height = :h "
            "WHERE tab = 'overview' AND widget_type = 'monthly_dynamics'"
        ).bindparams(h=dynamics_h)
    )
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET grid_y = :y "
            "WHERE tab = 'overview' "
            "  AND widget_type IN ('events_per_case_histogram', 'case_flow_cumulative')"
        ).bindparams(y=middle_y)
    )
    bind.execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET grid_y = :y "
            "WHERE tab = 'overview' "
            "  AND widget_type IN ('rework_table', 'top_paths_graph')"
        ).bindparams(y=bottom_y)
    )


def upgrade() -> None:
    _apply(dynamics_h=11, middle_y=14, bottom_y=19)


def downgrade() -> None:
    _apply(dynamics_h=10, middle_y=13, bottom_y=18)
