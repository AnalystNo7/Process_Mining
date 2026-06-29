"""rename rework widget title: переделок -> повторов

Revision ID: 015
Revises: 014
Create Date: 2026-06-29 16:00:00

Терминология «переделок» → «повторов». Переименовывает заголовок дефолтного
виджета «Таблица переделок» → «Таблица повторов» у существующих дашбордов.
Пользовательские заголовки (если меняли вручную) не трогаем — обновляем
только точное совпадение со старым дефолтом.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE core.dashboard_widgets SET title = 'Таблица повторов' "
            "WHERE widget_type = 'rework_table' AND title = 'Таблица переделок'"
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE core.dashboard_widgets SET title = 'Таблица переделок' "
            "WHERE widget_type = 'rework_table' AND title = 'Таблица повторов'"
        )
    )
