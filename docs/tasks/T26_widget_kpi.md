# T26: KPI-карточки

## Цель
Виджет `kpi_card` отображает одно число с подписью и опц. иконкой.

## Контекст
- `04_UI.md` раздел "kpi_card"
- `03_API.md` эндпоинт `GET /widgets/{id}/data`

## DoD
- [ ] Backend: `WidgetDataService.compute_kpi_card(vd, config, filters)` — обращается к cached_stats VD или считает на лету.
- [ ] Поддержка метрик: total_cases, total_events, unique_activities, unique_resources, unique_departments, global_rework_pct, variability_pct, mean_occurrence_pct, avg_case_duration_seconds, sla_compliance_pct (см. T34), cases_with_rework, cases_without_rework.
- [ ] Поддержка format: number (1 328), percent (20.06%), duration (22д 1ч 12м), datetime.
- [ ] React-компонент `<KpiCardWidget widgetId>` — fetch через React Query, AntD Card.
- [ ] Иконка из @ant-design/icons по имени из config.

## Реализация

### Backend
```python
def format_duration_seconds(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    return f"{hours}ч {minutes}м"

def format_value(value: float | int | str, fmt: str) -> str:
    if value is None:
        return "—"
    if fmt == "number":
        return f"{int(value):,}".replace(",", " ")
    if fmt == "percent":
        return f"{value:.2f}%".replace(".", ",")
    if fmt == "duration":
        return format_duration_seconds(value)
    return str(value)
```

### Frontend
```tsx
import { Card, Statistic } from "antd";
import { useQuery } from "@tanstack/react-query";

export function KpiCardWidget({ widgetId }: { widgetId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["widget-data", widgetId],
    queryFn: () => api.getWidgetData(widgetId),
  });
  
  if (isLoading) return <Card loading />;
  
  return (
    <Card title={data.title}>
      <Statistic value={data.formatted} valueStyle={{ fontSize: 32 }} />
    </Card>
  );
}
```

## Тесты
- `test_kpi_card_total_cases`.
- `test_kpi_card_format_duration`.
- `test_kpi_card_handles_null`.

## Acceptance
4 KPI-карточки на дефолтном дашборде синтетического VD показывают: 1328, 25606, 20.06%, 22д 1ч 12м.
