import { Empty, Statistic, Table, Tag, Typography, type TableColumnsType } from 'antd';
import type { Data, Layout } from 'plotly.js';

import type { CytoscapeElement } from '@/api/analytics';
import { Plot } from '@/components/Plot';
import { ProcessGraph } from '@/components/ProcessGraph';
import { formatDuration } from '@/lib/format';

interface XYPoint {
  x: string;
  y: number;
}

const CHART_HEIGHT = 280;

const BASE_LAYOUT: Partial<Layout> = {
  margin: { l: 56, r: 16, t: 16, b: 48 },
  autosize: true,
};

const PLOT_STYLE = { width: '100%', height: CHART_HEIGHT };
const PLOT_CONFIG = { displayModeBar: false, responsive: true };

function BarOrLine({
  data,
  mode,
}: {
  data: { data: XYPoint[]; x_label: string; y_label: string };
  mode: 'bar' | 'line';
}) {
  const trace = {
    x: data.data.map((p) => p.x),
    y: data.data.map((p) => p.y),
    type: mode === 'bar' ? 'bar' : 'scatter',
    mode: mode === 'line' ? 'lines+markers' : undefined,
    marker: { color: '#1677ff' },
  };
  return (
    <Plot
      data={[trace] as Data[]}
      layout={BASE_LAYOUT}
      style={PLOT_STYLE}
      config={PLOT_CONFIG}
      useResizeHandler
    />
  );
}

function MonthlyDynamics({
  data,
}: {
  data: { data: XYPoint[]; line_data: XYPoint[]; line_label: string };
}) {
  const traces = [
    {
      x: data.data.map((p) => p.x),
      y: data.data.map((p) => p.y),
      type: 'bar',
      name: 'Операции',
      marker: { color: '#1677ff' },
    },
    {
      x: data.line_data.map((p) => p.x),
      y: data.line_data.map((p) => p.y),
      type: 'scatter',
      mode: 'lines+markers',
      name: data.line_label,
      yaxis: 'y2',
      line: { color: '#fa8c16' },
    },
  ];
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    showlegend: true,
    legend: { orientation: 'h' },
    yaxis2: { overlaying: 'y', side: 'right' },
  };
  return (
    <Plot
      data={traces as Data[]}
      layout={layout}
      style={PLOT_STYLE}
      config={PLOT_CONFIG}
      useResizeHandler
    />
  );
}

function Heatmap({
  data,
}: {
  data: { cells: { x: string; y: string; value: number }[] };
}) {
  const xs = Array.from(new Set(data.cells.map((c) => c.x))).sort();
  const ys = Array.from(new Set(data.cells.map((c) => c.y))).sort();
  const lookup = new Map(data.cells.map((c) => [`${c.x}|${c.y}`, c.value]));
  const z = ys.map((y) => xs.map((x) => lookup.get(`${x}|${y}`) ?? 0));
  return (
    <Plot
      data={[{ type: 'heatmap', x: xs, y: ys, z, colorscale: 'Blues' }] as Data[]}
      layout={BASE_LAYOUT}
      style={PLOT_STYLE}
      config={PLOT_CONFIG}
      useResizeHandler
    />
  );
}

interface ReworkRow {
  activity: string;
  total: number;
  repeats: number;
  rework_pct: number;
}

function ReworkTable({ data }: { data: { rows: ReworkRow[]; global_rework_pct: number } }) {
  const columns: TableColumnsType<ReworkRow> = [
    { title: 'Операция', dataIndex: 'activity', key: 'activity' },
    { title: 'Всего', dataIndex: 'total', key: 'total', width: 90 },
    { title: 'Повторов', dataIndex: 'repeats', key: 'repeats', width: 100 },
    {
      title: '% переделок',
      dataIndex: 'rework_pct',
      key: 'rework_pct',
      width: 120,
      render: (value: number) => `${value.toFixed(1)}%`,
    },
  ];
  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
        Глобальный уровень переделок: {data.global_rework_pct.toFixed(2)}%
      </Typography.Paragraph>
      <Table
        rowKey="activity"
        size="small"
        columns={columns}
        dataSource={data.rows}
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
      />
    </div>
  );
}

interface ResourceRow {
  resource: string;
  n_cases: number;
  n_events: number;
  avg_own_duration_seconds: number;
  n_unique_activities: number;
}

function ResourceTable({ data }: { data: { rows: ResourceRow[] } }) {
  const columns: TableColumnsType<ResourceRow> = [
    { title: 'Ресурс', dataIndex: 'resource', key: 'resource' },
    { title: 'Кейсов', dataIndex: 'n_cases', key: 'n_cases', width: 90 },
    { title: 'Операций', dataIndex: 'n_events', key: 'n_events', width: 100 },
    {
      title: 'Ср. длительность',
      dataIndex: 'avg_own_duration_seconds',
      key: 'avg',
      width: 150,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Операций (уник.)',
      dataIndex: 'n_unique_activities',
      key: 'n_unique_activities',
      width: 140,
    },
  ];
  return (
    <Table
      rowKey="resource"
      size="small"
      columns={columns}
      dataSource={data.rows}
      pagination={{ pageSize: 8, hideOnSinglePage: true }}
    />
  );
}

interface SlaRow {
  activity: string;
  role: string;
  total_events: number;
  events_with_sla: number;
  overdue_count: number;
  compliance_pct: number | null;
  target_pct: number;
  status: string;
}

const SLA_STATUS_COLOR: Record<string, string> = {
  good: 'green',
  warning: 'orange',
  poor: 'red',
  no_rule: 'default',
};

function SlaTable({
  data,
}: {
  data: { rows: SlaRow[]; overall_compliance_pct: number | null };
}) {
  const columns: TableColumnsType<SlaRow> = [
    { title: 'Операция', dataIndex: 'activity', key: 'activity' },
    { title: 'Роль', dataIndex: 'role', key: 'role' },
    { title: 'Просрочено', dataIndex: 'overdue_count', key: 'overdue', width: 110 },
    {
      title: 'Соответствие',
      dataIndex: 'compliance_pct',
      key: 'compliance',
      width: 130,
      render: (value: number | null) => (value == null ? '—' : `${value.toFixed(1)}%`),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (status: string) => (
        <Tag color={SLA_STATUS_COLOR[status] ?? 'default'}>{status}</Tag>
      ),
    },
  ];
  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
        Общее соответствие SLA:{' '}
        {data.overall_compliance_pct == null
          ? '—'
          : `${data.overall_compliance_pct.toFixed(2)}%`}
      </Typography.Paragraph>
      <Table
        rowKey={(row) => `${row.activity}|${row.role}`}
        size="small"
        columns={columns}
        dataSource={data.rows}
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
      />
    </div>
  );
}

interface VariantRow {
  trace: string[];
  n_cases: number;
  avg_duration_seconds: number;
}

function TopPaths({ data }: { data: { variants: VariantRow[] } }) {
  const columns: TableColumnsType<VariantRow> = [
    {
      title: 'Маршрут',
      key: 'trace',
      render: (_, row) => row.trace.join(' → '),
    },
    { title: 'Кейсов', dataIndex: 'n_cases', key: 'n_cases', width: 90 },
    {
      title: 'Ср. длительность',
      dataIndex: 'avg_duration_seconds',
      key: 'avg',
      width: 150,
      render: (value: number) => formatDuration(value),
    },
  ];
  return (
    <Table
      rowKey={(_, index) => String(index)}
      size="small"
      columns={columns}
      dataSource={data.variants}
      pagination={false}
    />
  );
}

export function WidgetContent({
  type,
  data,
}: {
  type: string;
  data: Record<string, unknown>;
}) {
  switch (type) {
    case 'kpi_card': {
      const kpi = data as { formatted: string };
      return (
        <Statistic value={kpi.formatted} valueStyle={{ fontSize: 32 }} />
      );
    }
    case 'bar_chart':
      return <BarOrLine data={data as never} mode="bar" />;
    case 'line_chart':
      return <BarOrLine data={data as never} mode="line" />;
    case 'monthly_dynamics':
      return <MonthlyDynamics data={data as never} />;
    case 'heatmap':
      return <Heatmap data={data as never} />;
    case 'rework_table':
      return <ReworkTable data={data as never} />;
    case 'resource_analysis_table':
      return <ResourceTable data={data as never} />;
    case 'sla_compliance_table':
      return <SlaTable data={data as never} />;
    case 'top_paths_graph':
      return <TopPaths data={data as never} />;
    case 'process_graph': {
      const graph = data as { nodes: CytoscapeElement[]; edges: CytoscapeElement[] };
      return graph.nodes.length > 0 ? (
        <ProcessGraph nodes={graph.nodes} edges={graph.edges} height={360} />
      ) : (
        <Empty description="Недостаточно данных для графа" />
      );
    }
    default:
      return <Empty description={`Тип виджета «${type}» не поддерживается`} />;
  }
}
