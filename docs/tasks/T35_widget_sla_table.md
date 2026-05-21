# T35: SLA-compliance виджет

## Цель
Виджет `sla_compliance_table` для дашборда. Таблица с цветовой индикацией нарушений SLA.

## Контекст
- T34 — Расчёт SLA-комплаенса.
- `04_UI.md` раздел "Widget types".

## DoD
- [ ] Endpoint `GET /api/virtual-datasets/{id}/analytics/sla-compliance?filters=...`.
- [ ] React-компонент `<SlaComplianceTable>`.
- [ ] Возможность сортировки по любой колонке.
- [ ] Цветовая индикация ячеек compliance_pct (зелёный/жёлтый/красный по статусу из T34).

## Колонки таблицы
| Операция | Роль | Норматив | Событий | С SLA | Просрочек | % Компл. | Цель | Статус |
|----------|------|----------|---------|-------|-----------|----------|------|--------|

## Цветовая схема
- `compliance_pct >= target_pct` → зелёный (#52c41a)
- `compliance_pct >= target_pct - 5` → жёлтый (#faad14)
- `compliance_pct < target_pct - 5` → красный (#f5222d)

## Конфиг виджета
```json
{
  "type": "sla_compliance_table",
  "config": {
    "title": "SLA-комплаенс по операциям",
    "show_only_operations_with_rules": true,
    "sort_by": "compliance_pct",
    "sort_dir": "asc"
  }
}
```

## React-компонент
```tsx
const SlaComplianceTable = ({ virtualDatasetId, globalFilters, config }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['sla-compliance', virtualDatasetId, globalFilters],
    queryFn: () => api.get(`/virtual-datasets/${virtualDatasetId}/analytics/sla-compliance`, { params: { filters: JSON.stringify(globalFilters) }}),
  });

  if (isLoading) return <Skeleton />;
  
  const columns = [
    { title: 'Операция', dataIndex: 'activity', sorter: true },
    { title: 'Роль', dataIndex: 'role' },
    { title: 'Норматив', dataIndex: 'threshold_hours', render: h => formatDuration(h) },
    { title: 'Событий', dataIndex: 'total_events', sorter: (a,b) => a.total_events - b.total_events },
    { title: 'С SLA', dataIndex: 'events_with_sla' },
    { title: 'Просрочек', dataIndex: 'overdue_count', sorter: (a,b) => a.overdue_count - b.overdue_count },
    { title: '% Компл.', dataIndex: 'compliance_pct', sorter: (a,b) => a.compliance_pct - b.compliance_pct,
      render: pct => <Tag color={statusColor(pct, ...)}>{pct?.toFixed(1)}%</Tag> },
    { title: 'Цель', dataIndex: 'target_pct', render: v => `${v}%` },
    { title: 'Статус', dataIndex: 'status', render: s => <StatusBadge status={s} /> },
  ];
  
  const rows = config.show_only_operations_with_rules 
    ? data.rows.filter(r => r.sla_rule_id !== null) 
    : data.rows;
  
  return (
    <Card title={config.title}>
      <Table dataSource={rows} columns={columns} pagination={false} 
             rowKey="activity" size="small" />
      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
        Общий комплаенс: <strong>{data.overall_compliance_pct?.toFixed(1)}%</strong>
      </div>
    </Card>
  );
};
```

## Тесты
- `test_sla_table_shows_only_operations_with_rules` (когда show_only_operations_with_rules = true).
- `test_sorting_by_compliance_pct_asc` — топ нарушителей сверху.
- `test_color_coding_red_yellow_green`.
- E2E: добавление виджета на дашборд → виджет показывает корректные данные.

## Acceptance
На synthetic_log.xlsx + 11 SLA-правил виджет показывает таблицу с 11 ролевыми операциями + всеми остальными (если show_all = true). Топ-3 нарушителей (Юр.управление, ЭБ, Финансы) выделены красным.
