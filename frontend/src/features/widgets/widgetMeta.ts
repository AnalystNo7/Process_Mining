/** Метаданные типов виджетов для конструктора дашборда. */

export interface WidgetTypeOption {
  value: string;
  label: string;
}

export const WIDGET_TYPES: WidgetTypeOption[] = [
  { value: 'kpi_card', label: 'KPI-карточка' },
  { value: 'monthly_dynamics', label: 'Динамика по месяцам' },
  { value: 'bar_chart', label: 'Столбчатая диаграмма' },
  { value: 'line_chart', label: 'Линейный график' },
  { value: 'heatmap', label: 'Тепловая карта' },
  { value: 'rework_table', label: 'Таблица переделок' },
  { value: 'resource_analysis_table', label: 'Анализ ресурсов' },
  { value: 'sla_compliance_table', label: 'Соблюдение SLA' },
  { value: 'top_paths_graph', label: 'Топ маршрутов' },
  { value: 'process_graph', label: 'Граф процесса' },
];

export const WIDGET_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  WIDGET_TYPES.map((t) => [t.value, t.label])
);

export interface KpiMetricOption {
  value: string;
  label: string;
  format: 'number' | 'percent' | 'duration';
}

export const KPI_METRICS: KpiMetricOption[] = [
  { value: 'total_cases', label: 'Всего кейсов', format: 'number' },
  { value: 'total_events', label: 'Всего операций', format: 'number' },
  { value: 'unique_activities', label: 'Уникальных операций', format: 'number' },
  { value: 'unique_traces', label: 'Уникальных маршрутов', format: 'number' },
  { value: 'global_rework_pct', label: 'Доля переделок', format: 'percent' },
  { value: 'variability_pct', label: 'Вариативность процесса', format: 'percent' },
  {
    value: 'avg_case_duration_seconds',
    label: 'Средняя длительность кейса',
    format: 'duration',
  },
];

export const BAR_SOURCES: WidgetTypeOption[] = [
  { value: 'monthly_dynamics', label: 'Динамика по месяцам' },
  { value: 'top_departments', label: 'Топ подразделений' },
  { value: 'top_resources', label: 'Топ исполнителей' },
  { value: 'top_activities', label: 'Топ операций' },
];

export const HEATMAP_AXES: WidgetTypeOption[] = [
  { value: 'department', label: 'Подразделение' },
  { value: 'resource', label: 'Исполнитель' },
];
