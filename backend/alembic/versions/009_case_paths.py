"""case paths table

Revision ID: 009
Revises: 008
Create Date: 2026-06-23 15:00:00

T46 (Фаза 6). Создаёт таблицу `core.case_paths` для кэширования вариантов
процесса (DFG paths). Заполняется Celery-задачей `compute_virtual_dataset_stats`
после готовности VirtualDataset.

Структура:
- path_hash — 16 hex-символов sha1 от JSON-сериализованной последовательности
  активностей; стабильный ID для копирования в UI;
- activities — JSON массив имён операций варианта;
- n_cases, avg_duration_seconds, sample_case_ids — агрегаты по варианту;
- computed_at — таймстамп пересчёта (используется при принудительной
  ре-индексации).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_paths",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("virtual_dataset_id", sa.BigInteger(), nullable=False),
        sa.Column("path_hash", sa.String(length=16), nullable=False),
        sa.Column("activities", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("n_cases", sa.Integer(), nullable=False),
        sa.Column("avg_duration_seconds", sa.Float(), nullable=False),
        sa.Column("sample_case_ids", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["virtual_dataset_id"],
            ["core.virtual_datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "virtual_dataset_id", "path_hash", name="uq_case_paths_dataset_hash"
        ),
        schema="core",
    )
    op.create_index(
        "idx_case_paths_dataset",
        "case_paths",
        ["virtual_dataset_id"],
        schema="core",
    )
    op.create_index(
        "idx_case_paths_dataset_n_cases",
        "case_paths",
        ["virtual_dataset_id", "n_cases"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index("idx_case_paths_dataset_n_cases", table_name="case_paths", schema="core")
    op.drop_index("idx_case_paths_dataset", table_name="case_paths", schema="core")
    op.drop_table("case_paths", schema="core")
