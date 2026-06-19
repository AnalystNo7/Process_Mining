"""overview layout v2

Revision ID: 005
Revises: 004
Create Date: 2026-06-19 12:00:00

T41.1 (Фаза 6). Пересобирает виджеты вкладки «Обзор» (`tab='overview'`) у всех
существующих `standard_pm`-дашбордов под согласованную раскладку:

  ряд 1        — 4 KPI-карточки в строку;
  блок         — «Динамика по месяцам» (monthly_dynamics) 3/4 ширины слева +
                 столбик из 4 KPI справа (Начало/Конец/Вариативность/Встречаемость);
  ряд          — «Кол-во операций в экземпляре» | «Входящий и исходящий поток»;
  ряд          — «Топ повторов» (rework_table) | «Топ-5 путей процесса» (top_paths_graph).

Вкладки `process.*` и `details.*` не трогаются. Ручные правки вкладки «Обзор»
перезаписываются (согласовано). Набор синхронизирован с
`app/services/dashboard_service.py::_OVERVIEW_WIDGETS`.
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Целевой набор виджетов вкладки «Обзор» (порядок = порядок вставки).
# (widget_type, title, config, grid_x, grid_y, grid_width, grid_height)
_OVERVIEW: list[tuple[str, str, dict, int, int, int, int]] = [
    ("kpi_card", "Экземпляры", {"metric": "total_cases", "format": "number"}, 0, 0, 3, 2),
    ("kpi_card", "Операции", {"metric": "total_events", "format": "number"}, 3, 0, 3, 2),
    ("kpi_card", "Уникальные операции",
     {"metric": "unique_activities", "format": "number"}, 6, 0, 3, 2),
    ("kpi_card", "Средняя длительность",
     {"metric": "avg_case_duration_seconds", "format": "duration"}, 9, 0, 3, 2),
    ("monthly_dynamics", "Динамика по месяцам", {}, 0, 2, 9, 8),
    ("kpi_card", "Начало процесса",
     {"metric": "first_case_started_at", "format": "date"}, 9, 2, 3, 2),
    ("kpi_card", "Конец процесса",
     {"metric": "last_case_started_at", "format": "date"}, 9, 4, 3, 2),
    ("kpi_card", "Вариативность путей",
     {"metric": "variability_pct", "format": "percent"}, 9, 6, 3, 2),
    ("kpi_card", "Встречаемость операций",
     {"metric": "mean_occurrence_pct", "format": "percent"}, 9, 8, 3, 2),
    ("events_per_case_histogram", "Кол-во операций в экземпляре", {}, 0, 10, 6, 5),
    ("case_flow_cumulative", "Входящий и исходящий поток", {}, 6, 10, 6, 5),
    ("rework_table", "Топ повторов", {}, 0, 15, 6, 6),
    ("top_paths_graph", "Топ-5 путей процесса", {}, 6, 15, 6, 6),
]

# Прежний (T41) набор overview-виджетов — для downgrade (best-effort).
_OVERVIEW_LEGACY: list[tuple[str, str, dict, int, int, int, int]] = [
    ("kpi_card", "Экземпляры", {"metric": "total_cases", "format": "number"}, 0, 0, 3, 2),
    ("kpi_card", "Операции", {"metric": "total_events", "format": "number"}, 3, 0, 3, 2),
    ("kpi_card", "Уникальные операции",
     {"metric": "unique_activities", "format": "number"}, 6, 0, 3, 2),
    ("kpi_card", "Средняя длительность",
     {"metric": "avg_case_duration_seconds", "format": "duration"}, 9, 0, 3, 2),
    ("kpi_card", "Начало процесса",
     {"metric": "first_case_started_at", "format": "date"}, 0, 2, 3, 2),
    ("kpi_card", "Конец процесса",
     {"metric": "last_case_started_at", "format": "date"}, 3, 2, 3, 2),
    ("kpi_card", "Вариативность путей",
     {"metric": "variability_pct", "format": "percent"}, 6, 2, 3, 2),
    ("kpi_card", "Встречаемость операций",
     {"metric": "mean_occurrence_pct", "format": "percent"}, 9, 2, 3, 2),
    ("events_per_case_histogram", "Кол-во операций в экземпляре", {}, 0, 9, 12, 5),
    ("case_flow_cumulative", "Входящий и исходящий поток", {}, 0, 14, 12, 5),
]


def _rebuild_overview(
    widgets: list[tuple[str, str, dict, int, int, int, int]]
) -> None:
    bind = op.get_bind()
    dashboard_ids = bind.execute(
        sa.text(
            "SELECT id FROM core.dashboards WHERE template_kind = 'standard_pm'"
        )
    ).scalars().all()

    insert_sql = sa.text(
        """
        INSERT INTO core.dashboard_widgets
            (dashboard_id, widget_type, title, config, tab,
             use_global_filters, grid_x, grid_y, grid_width, grid_height)
        VALUES
            (:dashboard_id, :widget_type, :title, CAST(:config AS jsonb), 'overview',
             true, :grid_x, :grid_y, :grid_width, :grid_height)
        """
    )
    for dashboard_id in dashboard_ids:
        bind.execute(
            sa.text(
                "DELETE FROM core.dashboard_widgets "
                "WHERE dashboard_id = :did AND tab = 'overview'"
            ).bindparams(did=dashboard_id)
        )
        for wt, title, config, gx, gy, gw, gh in widgets:
            bind.execute(
                insert_sql.bindparams(
                    dashboard_id=dashboard_id,
                    widget_type=wt,
                    title=title,
                    config=json.dumps(config),
                    grid_x=gx,
                    grid_y=gy,
                    grid_width=gw,
                    grid_height=gh,
                )
            )


def upgrade() -> None:
    _rebuild_overview(_OVERVIEW)


def downgrade() -> None:
    # Best-effort: возвращаем прежний (T41) набор виджетов вкладки «Обзор».
    # Виджеты, добавленные пользователем вручную, не восстанавливаются.
    _rebuild_overview(_OVERVIEW_LEGACY)
