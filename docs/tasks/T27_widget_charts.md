# T27: Виджеты bar_chart, line_chart, heatmap, monthly_dynamics

## Цель
Все виджеты с графиками на Plotly.

## Контекст
- `04_UI.md` раздел "Каталог виджетов"

## DoD
- [ ] Backend `WidgetDataService.compute_bar_chart`, `compute_line_chart`, `compute_heatmap`, `compute_monthly_dynamics_chart`.
- [ ] Frontend компоненты `BarChartWidget`, `LineChartWidget`, `HeatmapWidget`, `MonthlyDynamicsWidget`.
- [ ] Используется `react-plotly.js`.
- [ ] Локализация: подписи на русском, числа в ru-RU.
- [ ] Поддержка config:
  - bar_chart: data_source, x_axis, y_axis, show_line_overlay, line_metric, limit, horizontal.
  - heatmap: x_axis, y_axis, metric, color_scheme.
  - monthly_dynamics: activity_filter, show_avg_sojourn_line.

## Реализация

### Backend (пример bar_chart)
```python
def compute_bar_chart(vd: VirtualDataset, config: dict, filters: dict) -> dict:
    df = load_filtered_df(vd, filters)
    
    if config["data_source"] == "monthly_dynamics":
        # Использует функцию из T22
        result = dynamics.compute_monthly_dynamics(df)
        return {
            "data": [{"x": str(row["month"]), "y": int(row["n_events"])} for _, row in result.iterrows()],
            "line_data": [{"x": str(row["month"]), "y": float(row["avg_sojourn_seconds"])} 
                          for _, row in result.iterrows()] if config.get("show_line_overlay") else None,
            "x_label": "Месяц",
            "y_label": "Количество операций",
            "line_label": "Ср. длительность с учётом перехода",
        }
    # ... остальные data_source аналогично
```

### Frontend (Plotly)
```tsx
import Plot from "react-plotly.js";

export function MonthlyDynamicsWidget({ widgetId }) {
  const { data } = useQuery({...});
  if (!data) return <Skeleton />;
  
  return (
    <Plot
      data={[
        { type: "bar", x: data.data.map(d=>d.x), y: data.data.map(d=>d.y),
          name: "Количество операций", yaxis: "y" },
        { type: "scatter", mode: "lines+markers", x: data.line_data?.map(d=>d.x),
          y: data.line_data?.map(d=>d.y), name: "Средняя длительность", yaxis: "y2" },
      ]}
      layout={{
        xaxis: { title: data.x_label },
        yaxis: { title: data.y_label },
        yaxis2: { title: data.line_label, overlaying: "y", side: "right" },
        height: 400,
      }}
      config={{ locale: "ru" }}
    />
  );
}
```

## Acceptance
Виджет monthly_dynamics на дашборде показывает столбцы и линию, идентичные слайдам 6, 11, 16 Газпрома (на synthetic_log).
