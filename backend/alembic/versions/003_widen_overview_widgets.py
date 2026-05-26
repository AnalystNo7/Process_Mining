"""widen overview widgets

Revision ID: 003
Revises: 002
Create Date: 2026-05-26 12:00:00

Расширяет виджеты «Кол-во операций в экземпляре» и «Входящий и исходящий
поток» дашборда «Обзор процесса» до w=12 для лучшей читаемости графиков.
Виджет «Операции» (operations_summary_short) в существующих дашбордах
не трогаем — react-grid-layout с compactType=vertical сам разместит его
ниже full-width виджетов при рендере.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE core.dashboard_widgets
        SET grid_x = 0, grid_width = 12
        WHERE widget_type = 'events_per_case_histogram'
        """
    )
    op.execute(
        """
        UPDATE core.dashboard_widgets
        SET grid_x = 0, grid_y = 14, grid_width = 12
        WHERE widget_type = 'case_flow_cumulative'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE core.dashboard_widgets
        SET grid_x = 0, grid_width = 4
        WHERE widget_type = 'events_per_case_histogram'
        """
    )
    op.execute(
        """
        UPDATE core.dashboard_widgets
        SET grid_x = 4, grid_y = 9, grid_width = 4
        WHERE widget_type = 'case_flow_cumulative'
        """
    )
