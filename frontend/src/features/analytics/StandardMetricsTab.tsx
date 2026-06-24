import { useQuery } from '@tanstack/react-query';
import { Card, Empty, Table, Typography, type TableColumnsType } from 'antd';

import {
  getEventsPerCaseDistribution,
  getOperations,
  type EventFilter,
  type EventsPerCaseBin,
  type OperationSummaryRow,
} from '@/api/analytics';
import { getVirtualDataset } from '@/api/virtualDatasets';
import { formatDateTime, formatDuration } from '@/lib/format';

/**
 * T42: подвкладка «Стандартные метрики» (REQ §6.7).
 * Три таблицы предрассчитанных показателей датасета:
 *   1) Базовые показатели (cached_stats) — KPI уровня датасета;
 *   2) Метрики операций — per-activity статистика;
 *   3) Распределение событий в кейсе — гистограмма.
 * Все эндпоинты переиспользуются: новый только /events-per-case-distribution.
 */
export function StandardMetricsTab({
  projectId,
  vdId,
  externalFilter,
}: {
  projectId: number;
  vdId: number;
  externalFilter?: EventFilter;
}) {
  const filterKey = JSON.stringify(externalFilter ?? {});

  const vdQuery = useQuery({
    queryKey: ['vd', vdId],
    queryFn: () => getVirtualDataset(projectId, vdId),
  });
  const opsQuery = useQuery({
    queryKey: ['standard-operations', projectId, vdId, filterKey],
    queryFn: () => getOperations(projectId, vdId, { filters: externalFilter }),
  });
  const histQuery = useQuery({
    queryKey: ['events-per-case-distribution', projectId, vdId, filterKey],
    queryFn: () =>
      getEventsPerCaseDistribution(projectId, vdId, { filters: externalFilter }),
  });

  const stats = (vdQuery.data?.cached_stats ?? {}) as Record<string, unknown>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card size="small" title="Показатели датасета" loading={vdQuery.isLoading}>
        {Object.keys(stats).length === 0 ? (
          <Empty description="Метрики ещё не посчитаны" />
        ) : (
          <DatasetMetricsTable stats={stats} />
        )}
      </Card>

      <Card size="small" title="Метрики операций" loading={opsQuery.isLoading}>
        <Table<OperationSummaryRow>
          rowKey="activity"
          size="small"
          dataSource={opsQuery.data?.items ?? []}
          columns={OPERATION_COLUMNS}
          pagination={{ pageSize: 20, hideOnSinglePage: true, showSizeChanger: false }}
          scroll={{ x: true }}
        />
      </Card>

      <Card
        size="small"
        title="Распределение событий в кейсе"
        loading={histQuery.isLoading}
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 0 }}>
          Всего кейсов: {histQuery.data?.total_cases ?? '—'}
        </Typography.Paragraph>
        <Table<EventsPerCaseBin>
          rowKey="events_in_case"
          size="small"
          dataSource={histQuery.data?.items ?? []}
          columns={HISTOGRAM_COLUMNS}
          pagination={{ pageSize: 20, hideOnSinglePage: true, showSizeChanger: false }}
        />
      </Card>
    </div>
  );
}

/* ─── Таблица 1: показатели датасета (key/value из cached_stats) ─── */

interface MetricRow {
  key: string;
  label: string;
  value: string;
}

const NUMBER_FMT = new Intl.NumberFormat('ru-RU');

function formatNumber(value: unknown): string {
  if (value == null) return '—';
  const num = Number(value);
  return Number.isFinite(num) ? NUMBER_FMT.format(num) : '—';
}

function formatPercent(value: unknown): string {
  if (value == null) return '—';
  const num = Number(value);
  return Number.isFinite(num) ? `${num.toFixed(2)}%` : '—';
}

/** Мета-описание метрик cached_stats: ключ → русская метка + форматтер. */
const METRIC_META: Array<{
  key: string;
  label: string;
  format: 'number' | 'percent' | 'duration' | 'date';
}> = [
  { key: 'total_cases', label: 'Всего кейсов', format: 'number' },
  { key: 'total_events', label: 'Всего событий', format: 'number' },
  { key: 'unique_activities', label: 'Уникальных операций', format: 'number' },
  { key: 'unique_resources', label: 'Уникальных исполнителей', format: 'number' },
  { key: 'unique_departments', label: 'Уникальных подразделений', format: 'number' },
  { key: 'unique_traces', label: 'Уникальных вариантов (трасс)', format: 'number' },
  { key: 'cases_with_rework', label: 'Кейсов с повторами', format: 'number' },
  { key: 'cases_without_rework', label: 'Кейсов без повторов', format: 'number' },
  { key: 'period_start', label: 'Период: от', format: 'date' },
  { key: 'period_end', label: 'Период: до', format: 'date' },
  { key: 'first_case_started_at', label: 'Первый кейс стартовал', format: 'date' },
  { key: 'last_case_started_at', label: 'Последний кейс стартовал', format: 'date' },
  {
    key: 'avg_case_duration_seconds',
    label: 'Средняя длительность кейса',
    format: 'duration',
  },
  {
    key: 'avg_case_duration_with_rework_seconds',
    label: 'Средняя длительность кейса с повторами',
    format: 'duration',
  },
  {
    key: 'avg_case_duration_without_rework_seconds',
    label: 'Средняя длительность кейса без повторов',
    format: 'duration',
  },
  { key: 'global_rework_pct', label: 'Глобальный % повторов', format: 'percent' },
  { key: 'variability_pct', label: 'Вариативность путей', format: 'percent' },
  {
    key: 'mean_occurrence_pct',
    label: 'Средняя встречаемость операции',
    format: 'percent',
  },
];

function formatMetric(value: unknown, kind: 'number' | 'percent' | 'duration' | 'date'): string {
  if (value == null || value === '') return '—';
  switch (kind) {
    case 'number':
      return formatNumber(value);
    case 'percent':
      return formatPercent(value);
    case 'duration':
      return formatDuration(Number(value));
    case 'date':
      return formatDateTime(String(value));
  }
}

function DatasetMetricsTable({ stats }: { stats: Record<string, unknown> }) {
  const rows: MetricRow[] = METRIC_META.map(({ key, label, format }) => ({
    key,
    label,
    value: formatMetric(stats[key], format),
  }));
  const columns: TableColumnsType<MetricRow> = [
    { title: 'Метрика', dataIndex: 'label', key: 'label' },
    { title: 'Значение', dataIndex: 'value', key: 'value', width: '40%' },
  ];
  return (
    <Table
      rowKey="key"
      size="small"
      columns={columns}
      dataSource={rows}
      pagination={false}
      showHeader={false}
    />
  );
}

/* ─── Таблица 2: метрики операций ─── */

const OPERATION_COLUMNS: TableColumnsType<OperationSummaryRow> = [
  { title: 'Операция', dataIndex: 'activity', key: 'activity' },
  { title: 'Кейсов', dataIndex: 'n_cases', key: 'n_cases', width: 100 },
  { title: 'Событий', dataIndex: 'n_events', key: 'n_events', width: 100 },
  {
    title: 'Ср. длительность',
    dataIndex: 'avg_own_duration_seconds',
    key: 'avg_own_duration_seconds',
    width: 160,
    render: (v: number) => formatDuration(v),
  },
  {
    title: 'Медиана',
    dataIndex: 'median_own_duration_seconds',
    key: 'median_own_duration_seconds',
    width: 160,
    render: (v: number) => formatDuration(v),
  },
  {
    title: 'Доля в кейсе',
    dataIndex: 'avg_share_pct',
    key: 'avg_share_pct',
    width: 130,
    render: (v: number) => `${v.toFixed(2)}%`,
  },
];

/* ─── Таблица 3: распределение событий в кейсе ─── */

const HISTOGRAM_COLUMNS: TableColumnsType<EventsPerCaseBin> = [
  {
    title: 'Событий в кейсе',
    dataIndex: 'events_in_case',
    key: 'events_in_case',
    width: 220,
  },
  { title: 'Число таких кейсов', dataIndex: 'n_cases', key: 'n_cases' },
];
