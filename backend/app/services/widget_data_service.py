"""Расчёт данных для отрисовки виджетов дашборда (см. 04_UI.md, T26-T29)."""

from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, EntityNotFoundError
from app.db.models.dashboards import Dashboard, DashboardWidget
from app.db.models.datasets import NamedSlice, VirtualDataset
from app.domain.mining.dynamics import (
    compute_case_flow,
    compute_events_per_case_histogram,
    compute_monthly_dynamics,
    compute_operations_dynamics,
)
from app.domain.mining.filters import parse_filters
from app.domain.mining.graph import build_dfg, filter_dfg
from app.domain.mining.resources import compute_resource_workload
from app.domain.mining.rework import (
    compute_global_rework_pct,
    compute_operation_summary_short,
    compute_rework_per_operation,
)
from app.domain.mining.sla import aggregate_sla_compliance, evaluate_sla
from app.domain.mining.variants import get_top_n_variants, get_variants_coverage
from app.domain.mining.workday import WorkdayCalculator
from app.domain.types import EventFilter
from app.services import analytics_service
from app.tasks.compute_stats import build_stats


def format_duration_seconds(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    return f"{hours}ч {minutes}м"


def format_value(value: Any, fmt: str) -> str:
    if value is None:
        return "—"
    if fmt == "number":
        return f"{int(value):,}".replace(",", " ")
    if fmt == "percent":
        return f"{float(value):.2f}%".replace(".", ",")
    if fmt == "duration":
        return format_duration_seconds(float(value))
    if fmt == "date":
        return str(value)[:10]
    return str(value)


_GRANULARITY_WIDGETS = {"operations_dynamics", "case_flow_cumulative"}


def _dashboard_granularity(dashboard: Dashboard) -> str:
    """Гранулярность из глобальных фильтров дашборда: D/W/M/Q. По умолчанию M."""
    if not dashboard.global_filters:
        return "M"
    value = str(dashboard.global_filters.get("granularity", "M")).upper()
    return value if value in {"D", "W", "M", "Q"} else "M"


async def _resolve_filter(
    db: AsyncSession, widget: DashboardWidget, dashboard: Dashboard
) -> EventFilter | None:
    """Эффективный фильтр виджета: локальный, либо глобальный дашборда,
    либо применённый именованный срез."""
    if not widget.use_global_filters:
        return parse_filters(widget.local_filters) if widget.local_filters else None
    if dashboard.applied_slice_id is not None:
        applied = await db.get(NamedSlice, dashboard.applied_slice_id)
        if applied is not None:
            return parse_filters(applied.filters)
    return parse_filters(dashboard.global_filters) if dashboard.global_filters else None


def _month_column(df: pd.DataFrame) -> pd.Series:
    return (
        df["timestamp_start"]
        .dt.tz_convert("Europe/Moscow")
        .dt.tz_localize(None)
        .dt.to_period("M")
        .astype(str)
    )


async def _kpi_card(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    metric = config.get("metric", "total_cases")
    fmt = config.get("format", "number")
    stats: dict[str, Any] | None = None
    if event_filter is None and virtual.cached_stats:
        stats = virtual.cached_stats
        if metric not in stats:  # старый кэш не содержит новые KPI — пересчёт
            stats = None
    if stats is None:
        df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
        stats = build_stats(df)
    value = stats.get(metric)
    return {"value": value, "formatted": format_value(value, fmt), "delta": None}


async def _monthly_dynamics(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    result = compute_monthly_dynamics(df, activity_filter=config.get("activity_filter"))
    return {
        "data": [
            {"x": str(row["month"]), "y": int(row["n_events"])}
            for _, row in result.iterrows()
        ],
        "line_data": [
            {"x": str(row["month"]), "y": float(row["avg_sojourn_seconds"])}
            for _, row in result.iterrows()
        ],
        "x_label": "Месяц",
        "y_label": "Количество операций",
        "line_label": "Средняя длительность с учётом перехода",
    }


_BAR_SOURCES = {
    "top_departments": "department",
    "top_resources": "resource",
    "top_activities": "activity",
}


async def _bar_or_line_chart(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    source = config.get("data_source", "monthly_dynamics")
    limit = int(config.get("limit", 20))

    if source == "monthly_dynamics":
        result = compute_monthly_dynamics(df)
        return {
            "data": [
                {"x": str(row["month"]), "y": int(row["n_events"])}
                for _, row in result.iterrows()
            ],
            "x_label": "Месяц",
            "y_label": "Количество операций",
        }

    column = _BAR_SOURCES.get(source)
    if column is None or column not in df.columns:
        raise BusinessRuleError(f"Неизвестный источник данных: {source}")
    counts = (
        df.dropna(subset=[column])
        .groupby(column)
        .size()
        .sort_values(ascending=False)
        .head(limit)
    )
    return {
        "data": [{"x": str(key), "y": int(val)} for key, val in counts.items()],
        "x_label": column,
        "y_label": "Количество операций",
    }


async def _heatmap(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    y_axis = config.get("y_axis", "department")
    if len(df) == 0 or y_axis not in df.columns:
        return {"cells": [], "x_label": "Месяц", "y_label": y_axis}
    work = df.dropna(subset=[y_axis]).copy()
    work["month"] = _month_column(work)
    grouped = work.groupby([y_axis, "month"]).size()
    return {
        "cells": [
            {"x": str(month), "y": str(key), "value": int(count)}
            for (key, month), count in grouped.items()
        ],
        "x_label": "Месяц",
        "y_label": y_axis,
    }


async def _rework_table(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    column = analytics_service.activity_column(config.get("activity_level", "raw"))
    limit = int(config.get("limit", 25))
    rework_df = compute_rework_per_operation(df, column)
    return {
        "rows": [
            {
                "activity": str(row["activity"]),
                "total": int(row["total"]),
                "repeats": int(row["repeats"]),
                "rework_pct": float(row["rework_pct"]),
            }
            for _, row in rework_df.head(limit).iterrows()
        ],
        "global_rework_pct": compute_global_rework_pct(df, column),
    }


async def _resource_analysis_table(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    limit = int(config.get("limit", 30))
    workload = compute_resource_workload(df)
    return {
        "rows": [
            {
                "resource": str(row["resource"]),
                "n_cases": int(row["n_cases"]),
                "n_events": int(row["n_events"]),
                "avg_own_duration_seconds": float(row["avg_own_duration_seconds"]),
                "n_unique_activities": int(row["n_unique_activities"]),
            }
            for _, row in workload.head(limit).iterrows()
        ]
    }


def _dfg_to_cytoscape(df: pd.DataFrame, column: str, min_edge_pct: float) -> dict[str, Any]:
    graph = filter_dfg(build_dfg(df, column), min_edge_pct)
    return {
        "nodes": [
            {
                "data": {
                    "id": node.activity,
                    "label": node.activity,
                    "count": node.count,
                    "avg_duration_sec": node.avg_own_duration_seconds,
                }
            }
            for node in graph.nodes
        ],
        "edges": [
            {
                "data": {
                    "id": f"{edge.from_activity}->{edge.to_activity}",
                    "source": edge.from_activity,
                    "target": edge.to_activity,
                    "count": edge.count,
                    "avg_duration_sec": edge.avg_duration_seconds,
                }
            }
            for edge in graph.edges
        ],
        "start_activities": graph.start_activities,
        "end_activities": graph.end_activities,
    }


async def _process_graph(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    column = analytics_service.activity_column(config.get("activity_level", "raw"))
    return _dfg_to_cytoscape(df, column, float(config.get("min_edge_frequency_pct", 0.0)))


async def _top_paths_graph(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    column = analytics_service.activity_column(config.get("activity_level", "raw"))
    n_paths = int(config.get("n_paths", 5))
    variants_df = get_top_n_variants(df, n=n_paths, activity_col=column)
    coverage = get_variants_coverage(df, n=n_paths, activity_col=column)
    return {
        "variants": [
            {
                "trace": list(row["trace"]),
                "n_cases": int(row["n_cases"]),
                "avg_duration_seconds": float(row["avg_duration_seconds"]),
            }
            for _, row in variants_df.iterrows()
        ],
        "coverage": coverage,
    }


async def _operations_dynamics(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    result = compute_operations_dynamics(df, granularity=str(config.get("granularity", "M")))
    return {
        "bars": [
            {"x": str(row["bucket"]), "y": int(row["n_events"])}
            for _, row in result.iterrows()
        ],
        "line": [
            {"x": str(row["bucket"]), "y": float(row["events_per_case"])}
            for _, row in result.iterrows()
        ],
        "bar_label": "Кол-во операций",
        "line_label": "Кол-во операций на экземпляр",
        "granularity": str(config.get("granularity", "M")),
    }


async def _events_per_case_histogram(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    hist = compute_events_per_case_histogram(df)
    return {
        "data": [
            {"x": int(row["events_in_case"]), "y": int(row["n_cases"])}
            for _, row in hist.iterrows()
        ],
        "x_label": "Кол-во операций в экземпляре",
        "y_label": "Кол-во экземпляров",
    }


async def _case_flow_cumulative(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    flow = compute_case_flow(df, granularity=str(config.get("granularity", "M")))
    return {
        "inflow": [
            {"x": str(row["bucket"]), "y": int(row["cum_started"])}
            for _, row in flow.iterrows()
        ],
        "outflow": [
            {"x": str(row["bucket"]), "y": int(row["cum_ended"])}
            for _, row in flow.iterrows()
        ],
        "inflow_label": "Входящий поток",
        "outflow_label": "Исходящий поток",
        "granularity": str(config.get("granularity", "M")),
    }


async def _operations_summary_short(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    column = analytics_service.activity_column(config.get("activity_level", "raw"))
    summary = compute_operation_summary_short(df, column)
    limit = int(config.get("limit", 50))
    return {
        "rows": [
            {
                "activity": str(row["activity"]),
                "pct_cases": float(row["pct_cases"]),
                "avg_own_duration_seconds": float(row["avg_own_duration_seconds"]),
                "rework_pct": float(row["rework_pct"]),
            }
            for _, row in summary.head(limit).iterrows()
        ]
    }


async def _sla_compliance_table(
    db: AsyncSession, virtual: VirtualDataset, config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    evaluated = evaluate_sla(df, virtual.sla_rules_snapshot, WorkdayCalculator())
    result = aggregate_sla_compliance(evaluated)
    rows = result["rows"]
    if config.get("show_only_operations_with_rules"):
        rows = [row for row in rows if row["events_with_sla"] > 0]
    return {"rows": rows, "overall_compliance_pct": result["overall_compliance_pct"]}


_HANDLERS = {
    "kpi_card": _kpi_card,
    "monthly_dynamics": _monthly_dynamics,
    "operations_dynamics": _operations_dynamics,
    "events_per_case_histogram": _events_per_case_histogram,
    "case_flow_cumulative": _case_flow_cumulative,
    "operations_summary_short": _operations_summary_short,
    "bar_chart": _bar_or_line_chart,
    "line_chart": _bar_or_line_chart,
    "heatmap": _heatmap,
    "rework_table": _rework_table,
    "resource_analysis_table": _resource_analysis_table,
    "process_graph": _process_graph,
    "top_paths_graph": _top_paths_graph,
    "sla_compliance_table": _sla_compliance_table,
}


async def compute_widget_data(db: AsyncSession, widget: DashboardWidget) -> dict[str, Any]:
    """Считает данные виджета: применяет фильтры, вызывает нужный алгоритм."""
    dashboard = await db.get(Dashboard, widget.dashboard_id)
    if dashboard is None:
        raise EntityNotFoundError("Дашборд виджета не найден")
    virtual = await db.get(VirtualDataset, dashboard.virtual_dataset_id)
    if virtual is None:
        raise EntityNotFoundError("Виртуальный датасет не найден")

    handler = _HANDLERS.get(widget.widget_type)
    if handler is None:
        raise BusinessRuleError(
            f"Виджет типа {widget.widget_type!r} пока не поддерживается"
        )
    event_filter = await _resolve_filter(db, widget, dashboard)
    config = dict(widget.config or {})
    if widget.widget_type in _GRANULARITY_WIDGETS and "granularity" not in config:
        config["granularity"] = _dashboard_granularity(dashboard)
    return await handler(db, virtual, config, event_filter)
