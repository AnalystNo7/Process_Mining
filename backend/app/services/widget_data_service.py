"""Расчёт данных для отрисовки виджетов дашборда (см. 04_UI.md, T26-T29)."""

from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, EntityNotFoundError
from app.db.models.dashboards import Dashboard, DashboardWidget
from app.db.models.datasets import VirtualDataset
from app.domain.mining.dynamics import compute_monthly_dynamics
from app.domain.mining.filters import parse_filters
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
    return str(value)


def _resolve_filter(
    widget: DashboardWidget, dashboard: Dashboard
) -> EventFilter | None:
    raw = dashboard.global_filters if widget.use_global_filters else widget.local_filters
    return parse_filters(raw) if raw else None


def _month_column(df: pd.DataFrame) -> pd.Series:
    return (
        df["timestamp_start"]
        .dt.tz_convert("Europe/Moscow")
        .dt.tz_localize(None)
        .dt.to_period("M")
        .astype(str)
    )


async def _kpi_card(
    db: AsyncSession,
    virtual: VirtualDataset,
    config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    metric = config.get("metric", "total_cases")
    fmt = config.get("format", "number")
    if event_filter is None and virtual.cached_stats:
        stats: dict[str, Any] = virtual.cached_stats
    else:
        df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
        stats = build_stats(df)
    value = stats.get(metric)
    return {"value": value, "formatted": format_value(value, fmt), "delta": None}


async def _monthly_dynamics(
    db: AsyncSession,
    virtual: VirtualDataset,
    config: dict[str, Any],
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
    db: AsyncSession,
    virtual: VirtualDataset,
    config: dict[str, Any],
    event_filter: EventFilter | None,
) -> dict[str, Any]:
    df = await analytics_service.load_vd_dataframe(db, virtual, event_filter)
    source = config.get("data_source", "monthly_dynamics")
    limit = int(config.get("limit", 20))

    if source == "monthly_dynamics":
        result = compute_monthly_dynamics(df)
        data = [
            {"x": str(row["month"]), "y": int(row["n_events"])}
            for _, row in result.iterrows()
        ]
        return {"data": data, "x_label": "Месяц", "y_label": "Количество операций"}

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
    db: AsyncSession,
    virtual: VirtualDataset,
    config: dict[str, Any],
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


_HANDLERS = {
    "kpi_card": _kpi_card,
    "monthly_dynamics": _monthly_dynamics,
    "bar_chart": _bar_or_line_chart,
    "line_chart": _bar_or_line_chart,
    "heatmap": _heatmap,
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
    event_filter = _resolve_filter(widget, dashboard)
    return await handler(db, virtual, widget.config, event_filter)
