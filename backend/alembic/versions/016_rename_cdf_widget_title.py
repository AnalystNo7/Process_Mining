"""rename case_duration_cdf widget title: убрать «(SLA)»

Revision ID: 016
Revises: 015
Create Date: 2026-06-30 12:00:00

Цель SLA теперь задаётся вручную на дашборде, поэтому «(SLA)» из заголовка
дефолтного виджета «Кривая длительности кейсов (SLA)» убираем. Обновляем только
точное совпадение со старым дефолтом — пользовательские заголовки не трогаем.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET title = 'Кривая длительности кейсов' "
            "WHERE widget_type = 'case_duration_cdf' "
            "AND title = 'Кривая длительности кейсов (SLA)'"
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE core.dashboard_widgets "
            "SET title = 'Кривая длительности кейсов (SLA)' "
            "WHERE widget_type = 'case_duration_cdf' "
            "AND title = 'Кривая длительности кейсов'"
        )
    )
