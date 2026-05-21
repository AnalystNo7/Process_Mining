"""seed global role templates

Revision ID: 002
Revises: 001
Create Date: 2026-05-21 11:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Базовый набор ролей и паттернов авто-разметки (02_DOMAIN_LOGIC.md).
DEFAULT_ROLE_TEMPLATES: list[dict[str, object]] = [
    {"role_name": "Инициатор", "patterns": []},
    {
        "role_name": "Юридическое управление",
        "patterns": ["Юридическое управление", "Юр.управление", "ЮУ", "правовой поддержки"],
    },
    {
        "role_name": "Финансовый блок",
        "patterns": [
            "Финансовое управление",
            "Отдел финансового планирования",
            "ОФП",
            "Казначей",
            "казначейск",
        ],
    },
    {
        "role_name": "Бухгалтерия",
        "patterns": ["бухгалтерского учета", "Бухгалтер", "налогооблож"],
    },
    {"role_name": "Экономическая безопасность", "patterns": ["экономической безопасности"]},
    {
        "role_name": "Закупки",
        "patterns": [
            "Управление закупок",
            "Отдел планирования и организации закупок",
            "закупок",
        ],
    },
    {"role_name": "Договорной отдел", "patterns": ["Договорной отдел"]},
    {
        "role_name": "Высшее руководство",
        "patterns": ["Генеральный директор", "Заместитель генерального"],
    },
    {
        "role_name": "Документооборот",
        "patterns": ["документационного обеспечения", "организационного обеспечения"],
    },
    {
        "role_name": "Информационная безопасность",
        "patterns": ["информационной безопасности", "корпоративной защиты"],
    },
]


def upgrade() -> None:
    templates = sa.table(
        "global_role_templates",
        sa.column("role_name", sa.String),
        sa.column("patterns", postgresql.JSONB),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        schema="core",
    )
    op.bulk_insert(
        templates,
        [
            {
                "role_name": tpl["role_name"],
                "patterns": tpl["patterns"],
                "sort_order": (idx + 1) * 10,
                "is_active": True,
            }
            for idx, tpl in enumerate(DEFAULT_ROLE_TEMPLATES)
        ],
    )


def downgrade() -> None:
    role_names = tuple(str(tpl["role_name"]) for tpl in DEFAULT_ROLE_TEMPLATES)
    op.execute(
        sa.text("DELETE FROM core.global_role_templates WHERE role_name IN :names").bindparams(
            sa.bindparam("names", value=role_names, expanding=True)
        )
    )
