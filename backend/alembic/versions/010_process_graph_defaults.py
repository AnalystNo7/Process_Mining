"""process graph safe defaults

Revision ID: 010
Revises: 009
Create Date: 2026-06-23 16:00:00

T43.1 (Фаза 6). Выставляет безопасный config для виджетов process_graph,
у которых он сейчас пустой ({}). Без `max_nodes` Cytoscape dagre-layout
зависает на крупных датасетах (50+ узлов).

Идемпотентность: применяется только к виджетам, у которых в config нет
ключа `max_nodes` (NEW: на свежих VirtualDataset виджет уже создаётся
с правильным конфигом, см. `_PROCESS_WIDGETS`).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE core.dashboard_widgets
            SET config = jsonb_build_object(
                'max_nodes', 60,
                'min_edge_frequency_pct', 5.0
            )
            WHERE widget_type = 'process_graph'
              AND tab = 'process.process'
              AND NOT (config ? 'max_nodes')
            """
        )
    )


def downgrade() -> None:
    # Возвращаем пустой config процесс-графам (best-effort).
    op.execute(
        sa.text(
            """
            UPDATE core.dashboard_widgets
            SET config = '{}'::jsonb
            WHERE widget_type = 'process_graph'
              AND tab = 'process.process'
              AND config @> '{"max_nodes": 60, "min_edge_frequency_pct": 5.0}'::jsonb
            """
        )
    )
