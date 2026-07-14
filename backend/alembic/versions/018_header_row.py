"""header_row: строка заголовков файла в датасетах и шаблонах загрузки

Revision ID: 018
Revises: 017
Create Date: 2026-07-14 15:00:00

Выбор строки заголовков в мастере загрузки: у Excel-файлов с шапкой отчёта
настоящие заголовки колонок не на первой строке. Номер строки (0-based)
хранится в физ.датасете (используется при парсинге в Celery) и в шаблоне
загрузки. Существующие записи — header_row=0 (прежнее поведение).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "physical_datasets",
        sa.Column("header_row", sa.Integer(), nullable=False, server_default="0"),
        schema="core",
    )
    op.add_column(
        "upload_templates",
        sa.Column("header_row", sa.Integer(), nullable=False, server_default="0"),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("upload_templates", "header_row", schema="core")
    op.drop_column("physical_datasets", "header_row", schema="core")
