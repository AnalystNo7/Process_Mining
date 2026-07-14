"""sheet_name: выбор листа Excel в датасетах и шаблонах загрузки

Revision ID: 019
Revises: 018
Create Date: 2026-07-14 16:00:00

Выбор листа в мастере загрузки: Excel-файлы содержат несколько листов, а
парсинг читал только первый. Имя выбранного листа хранится в физ.датасете
(используется при парсинге в Celery) и в шаблоне загрузки. NULL — первый лист
(прежнее поведение для существующих записей).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "physical_datasets",
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        schema="core",
    )
    op.add_column(
        "upload_templates",
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("upload_templates", "sheet_name", schema="core")
    op.drop_column("physical_datasets", "sheet_name", schema="core")
