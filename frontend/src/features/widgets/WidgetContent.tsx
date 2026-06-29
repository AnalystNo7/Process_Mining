import { Empty, Table, Tag, Typography, type TableColumnsType } from 'antd';
import type { Data, Layout } from 'plotly.js';

import type { CytoscapeElement } from '@/api/analytics';
import { Plot } from '@/components/Plot';
import { ProcessGraph } from '@/components/ProcessGraph';
import { formatDuration } from '@/lib/format';
import {
  DEFAULT_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS_STR,
  TWO_STATE_SORT_DIRECTIONS,
} from '@/lib/table';

/**
 * T49: общий конфиг пагинации для табличных виджетов дашборда.
 * Селектор «20 / 50 / 100 / 500» строк, автоскрытие на одной странице.
 */
const TABLE_PAGINATION_BIG = {
  defaultPageSize: DEFAULT_PAGE_SIZE,
  showSizeChanger: true,
  pageSizeOptions: TABLE_PAGE_SIZE_OPTIONS_STR,
  hideOnSinglePage: true,
} as const;

interface XYPoint {
  x: string;
  y: number;
}

const BASE_LAYOUT: Partial<Layout> = {
  margin: { l: 56, r: 16, t: 16, b: 48 },
  autosize: true,
};

// Plot занимает всю доступную высоту/ширину карточки. WidgetCard.body — flex-колонка
// (см. WidgetCard.tsx); снаружи Plot обёрнут в `PlotBox` с flex:1, чтобы Plotly
// получал реальную высоту контейнера и пересчитывал размеры через useResizeHandler.
const PLOT_STYLE = { width: '100%', height: '100%' };
const PLOT_CONFIG = { displayModeBar: false, responsive: true };

const PLOT_BOX_STYLE: React.CSSProperties = {
  flex: 1,
  minHeight: 0,
  display: 'flex',
  width: '100%',
};

function PlotBox({ children }: { children: React.ReactNode }) {
  return <div style={PLOT_BOX_STYLE}>{children}</div>;
}

/** Обрезает длинную подпись до max символов с многоточием. Полное имя
 * показывается в подсказке (hover) — см. виджеты длительности. */
function truncateLabel(s: string, max = 32): string {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

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
    <PlotBox>
      <Plot
        data={[trace] as Data[]}
        layout={BASE_LAYOUT}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
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
    <PlotBox>
      <Plot
        data={traces as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
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
    <PlotBox>
      <Plot
        data={[{ type: 'heatmap', x: xs, y: ys, z, colorscale: 'Blues' }] as Data[]}
        layout={BASE_LAYOUT}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
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
    {
      title: 'Операция',
      dataIndex: 'activity',
      key: 'activity',
      sorter: (a, b) => a.activity.localeCompare(b.activity, 'ru'),
    },
    {
      title: 'Всего',
      dataIndex: 'total',
      key: 'total',
      width: 90,
      sorter: (a, b) => a.total - b.total,
    },
    {
      title: 'Повторов',
      dataIndex: 'repeats',
      key: 'repeats',
      width: 100,
      sorter: (a, b) => a.repeats - b.repeats,
    },
    {
      title: '% переделок',
      dataIndex: 'rework_pct',
      key: 'rework_pct',
      width: 120,
      sorter: (a, b) => a.rework_pct - b.rework_pct,
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
        sortDirections={TWO_STATE_SORT_DIRECTIONS}
      pagination={TABLE_PAGINATION_BIG}
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
    {
      title: 'Ресурс',
      dataIndex: 'resource',
      key: 'resource',
      sorter: (a, b) => a.resource.localeCompare(b.resource, 'ru'),
    },
    {
      title: 'Кейсов',
      dataIndex: 'n_cases',
      key: 'n_cases',
      width: 90,
      sorter: (a, b) => a.n_cases - b.n_cases,
    },
    {
      title: 'Операций',
      dataIndex: 'n_events',
      key: 'n_events',
      width: 100,
      sorter: (a, b) => a.n_events - b.n_events,
    },
    {
      title: 'Ср. длительность',
      dataIndex: 'avg_own_duration_seconds',
      key: 'avg',
      width: 150,
      sorter: (a, b) => a.avg_own_duration_seconds - b.avg_own_duration_seconds,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Операций (уник.)',
      dataIndex: 'n_unique_activities',
      key: 'n_unique_activities',
      width: 140,
      sorter: (a, b) => a.n_unique_activities - b.n_unique_activities,
    },
  ];
  return (
    <Table
      rowKey="resource"
      size="small"
      columns={columns}
      dataSource={data.rows}
      sortDirections={TWO_STATE_SORT_DIRECTIONS}
      pagination={TABLE_PAGINATION_BIG}
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
    {
      title: 'Операция',
      dataIndex: 'activity',
      key: 'activity',
      sorter: (a, b) => a.activity.localeCompare(b.activity, 'ru'),
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      key: 'role',
      sorter: (a, b) => a.role.localeCompare(b.role, 'ru'),
    },
    {
      title: 'Просрочено',
      dataIndex: 'overdue_count',
      key: 'overdue',
      width: 110,
      sorter: (a, b) => a.overdue_count - b.overdue_count,
    },
    {
      title: 'Соответствие',
      dataIndex: 'compliance_pct',
      key: 'compliance',
      width: 130,
      sorter: (a, b) => (a.compliance_pct ?? -1) - (b.compliance_pct ?? -1),
      render: (value: number | null) => (value == null ? '—' : `${value.toFixed(1)}%`),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      sorter: (a, b) => a.status.localeCompare(b.status),
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
        sortDirections={TWO_STATE_SORT_DIRECTIONS}
      pagination={TABLE_PAGINATION_BIG}
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
      sorter: (a, b) => a.trace.length - b.trace.length,
      render: (_, row) => row.trace.join(' → '),
    },
    {
      title: 'Кейсов',
      dataIndex: 'n_cases',
      key: 'n_cases',
      width: 90,
      sorter: (a, b) => a.n_cases - b.n_cases,
    },
    {
      title: 'Ср. длительность',
      dataIndex: 'avg_duration_seconds',
      key: 'avg',
      width: 150,
      sorter: (a, b) => a.avg_duration_seconds - b.avg_duration_seconds,
      render: (value: number) => formatDuration(value),
    },
  ];
  return (
    <Table
      rowKey={(_, index) => String(index)}
      size="small"
      columns={columns}
      dataSource={data.variants}
      sortDirections={TWO_STATE_SORT_DIRECTIONS}
      pagination={TABLE_PAGINATION_BIG}
    />
  );
}

function OperationsDynamics({
  data,
}: {
  data: { bars: XYPoint[]; line: XYPoint[]; bar_label: string; line_label: string };
}) {
  const traces = [
    {
      x: data.bars.map((p) => p.x),
      y: data.bars.map((p) => p.y),
      type: 'bar',
      name: data.bar_label,
      marker: { color: '#1677ff' },
    },
    {
      x: data.line.map((p) => p.x),
      y: data.line.map((p) => p.y),
      type: 'scatter',
      mode: 'lines+markers',
      name: data.line_label,
      yaxis: 'y2',
      line: { color: '#13c2c2' },
    },
  ];
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    showlegend: true,
    legend: { orientation: 'h' },
    yaxis: { title: { text: 'Кол-во операций' } },
    yaxis2: { overlaying: 'y', side: 'right', title: { text: 'Операций на экз.' } },
  };
  return (
    <PlotBox>
      <Plot
        data={traces as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
  );
}

function EventsPerCaseHistogram({
  data,
}: {
  data: { data: { x: number; y: number }[]; x_label: string; y_label: string };
}) {
  const trace = {
    x: data.data.map((p) => p.x),
    y: data.data.map((p) => p.y),
    type: 'bar',
    marker: { color: '#722ed1' },
  };
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    xaxis: { title: { text: data.x_label }, tickmode: 'linear' },
    yaxis: { title: { text: data.y_label } },
  };
  return (
    <PlotBox>
      <Plot
        data={[trace] as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
  );
}

function CaseFlow({
  data,
}: {
  data: {
    inflow: XYPoint[];
    outflow: XYPoint[];
    inflow_label: string;
    outflow_label: string;
  };
}) {
  const traces = [
    {
      x: data.inflow.map((p) => p.x),
      y: data.inflow.map((p) => p.y),
      type: 'scatter',
      mode: 'lines',
      name: data.inflow_label,
      fill: 'tozeroy',
      line: { color: '#1677ff' },
      fillcolor: 'rgba(22,119,255,0.2)',
    },
    {
      x: data.outflow.map((p) => p.x),
      y: data.outflow.map((p) => p.y),
      type: 'scatter',
      mode: 'lines',
      name: data.outflow_label,
      fill: 'tozeroy',
      line: { color: '#f5222d' },
      fillcolor: 'rgba(245,34,45,0.2)',
    },
  ];
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    showlegend: true,
    legend: { orientation: 'h' },
  };
  return (
    <PlotBox>
      <Plot
        data={traces as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
  );
}

interface OperationSummaryShortRow {
  activity: string;
  pct_cases: number;
  avg_own_duration_seconds: number;
  rework_pct: number;
}

function OperationsSummaryShort({
  data,
}: {
  data: { rows: OperationSummaryShortRow[] };
}) {
  const columns: TableColumnsType<OperationSummaryShortRow> = [
    {
      title: 'Операция',
      dataIndex: 'activity',
      key: 'activity',
      width: '45%',
      sorter: (a, b) => a.activity.localeCompare(b.activity, 'ru'),
      onCell: () => ({ style: { whiteSpace: 'normal', wordBreak: 'break-word' } }),
    },
    {
      title: '% в экз.',
      dataIndex: 'pct_cases',
      key: 'pct_cases',
      width: 90,
      align: 'right',
      sorter: (a, b) => a.pct_cases - b.pct_cases,
      render: (value: number) => `${value.toFixed(1)}%`,
    },
    {
      title: 't (avg)',
      dataIndex: 'avg_own_duration_seconds',
      key: 'avg',
      width: 110,
      align: 'right',
      sorter: (a, b) => a.avg_own_duration_seconds - b.avg_own_duration_seconds,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Зацикл.',
      dataIndex: 'rework_pct',
      key: 'rework',
      width: 90,
      align: 'right',
      sorter: (a, b) => a.rework_pct - b.rework_pct,
      render: (value: number) => `${value.toFixed(1)}%`,
    },
  ];
  return (
    <Table
      rowKey="activity"
      size="small"
      columns={columns}
      dataSource={data.rows}
      sortDirections={TWO_STATE_SORT_DIRECTIONS}
      pagination={TABLE_PAGINATION_BIG}
    />
  );
}

interface BoxplotTrace {
  name: string;
  y: number[];
  n: number;
  q1: number;
  median: number;
  q3: number;
  mean: number;
  min: number;
  max: number;
}

function OperationDurationsBoxplot({
  data,
}: {
  data: { traces: BoxplotTrace[] };
}) {
  if (!data.traces || data.traces.length === 0) {
    return <Empty description="Нет данных для построения" />;
  }
  // T45: один Plotly box-trace на операцию. boxmean: true рисует пунктирную
  // линию среднего поверх медианы — позволяет видеть скос распределения.
  const traces = data.traces.map((tr) => ({
    type: 'box',
    name: tr.name,
    y: tr.y,
    boxmean: true,
    marker: { color: '#1677ff' },
    line: { color: '#1677ff' },
  }));
  const names = data.traces.map((tr) => tr.name);
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    margin: { l: 64, r: 16, t: 16, b: 120 },
    showlegend: false,
    yaxis: { title: { text: 'Длительность (сек)' } },
    // Полное имя операции остаётся в name (видно в hover), подпись по оси
    // обрезается, чтобы длинные названия не налезали друг на друга.
    xaxis: {
      tickmode: 'array',
      tickvals: names,
      ticktext: names.map((n) => truncateLabel(n, 24)),
      tickangle: -30,
      automargin: true,
    },
  };
  return (
    <PlotBox>
      <Plot
        data={traces as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
  );
}

interface CdfPoint {
  x: number;
  y: number;
}

function CaseDurationCdf({
  data,
}: {
  data: {
    points: CdfPoint[];
    sla_target_seconds: number | null;
    pct_within_sla: number | null;
    x_label: string;
    y_label: string;
  };
}) {
  if (!data.points || data.points.length === 0) {
    return <Empty description="Нет данных для построения" />;
  }
  const trace = {
    x: data.points.map((p) => p.x),
    y: data.points.map((p) => p.y),
    type: 'scatter',
    mode: 'lines',
    line: { color: '#1677ff', shape: 'hv' },
    hovertemplate: '%{y:.1f}% ≤ %{x:.0f} сек<extra></extra>',
  };
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    yaxis: { title: { text: data.y_label }, range: [0, 100] },
    xaxis: { title: { text: data.x_label } },
  };
  // Вертикальная линия SLA + подпись «X% уложились».
  if (data.sla_target_seconds != null) {
    layout.shapes = [
      {
        type: 'line',
        x0: data.sla_target_seconds,
        x1: data.sla_target_seconds,
        y0: 0,
        y1: 100,
        line: { color: '#cf1322', width: 2, dash: 'dash' },
      },
    ];
    layout.annotations = [
      {
        x: data.sla_target_seconds,
        y: 100,
        yanchor: 'bottom',
        showarrow: false,
        text:
          data.pct_within_sla != null
            ? `SLA ${formatDuration(data.sla_target_seconds)} · ${data.pct_within_sla.toFixed(0)}% уложились`
            : `SLA ${formatDuration(data.sla_target_seconds)}`,
        font: { color: '#cf1322' },
      },
    ];
  }
  return (
    <PlotBox>
      <Plot
        data={[trace] as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
  );
}

function DurationBottleneckHeatmap({
  data,
}: {
  data: {
    cells: { x: string; y: string; value: number }[];
    x_categories: string[];
    y_categories: string[];
    x_label: string;
    y_label: string;
  };
}) {
  if (!data.cells || data.cells.length === 0) {
    return <Empty description="Нет данных для построения" />;
  }
  // Операции — по Y (в порядке ранга, топ-1 наверху за счёт reversed),
  // разрез (департамент/исполнитель) — по X. Подписи обеих осей обрезаются,
  // полное имя и человекочитаемая длительность — в подсказке.
  const ys = data.y_categories;
  const xs = data.x_categories;
  const lookup = new Map(data.cells.map((c) => [`${c.x}|${c.y}`, c.value]));
  const z = ys.map((y) => xs.map((x) => lookup.get(`${x}|${y}`) ?? null));
  const text = ys.map((y) =>
    xs.map((x) => {
      const v = lookup.get(`${x}|${y}`);
      return v == null ? '' : `${y}<br>${x}<br>медиана: ${formatDuration(v)}`;
    }),
  );
  // Шкала цвета в человекочитаемых единицах: 4 равномерные засечки.
  const vals = data.cells.map((c) => c.value);
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  const tickvals = [0, 1, 2, 3].map((i) => mn + ((mx - mn) * i) / 3);
  return (
    <PlotBox>
      <Plot
        data={
          [
            {
              type: 'heatmap',
              x: xs,
              y: ys,
              z,
              text,
              hoverinfo: 'text',
              colorscale: 'Reds',
              colorbar: {
                tickvals,
                ticktext: tickvals.map((v) => formatDuration(v)),
              },
            },
          ] as unknown as Data[]
        }
        layout={{
          ...BASE_LAYOUT,
          margin: { l: 240, r: 16, t: 16, b: 80 },
          xaxis: {
            title: { text: data.x_label },
            tickmode: 'array',
            tickvals: xs,
            ticktext: xs.map((s) => truncateLabel(s, 20)),
            tickangle: -20,
            automargin: true,
          },
          yaxis: {
            tickmode: 'array',
            tickvals: ys,
            ticktext: ys.map((s) => truncateLabel(s, 40)),
            autorange: 'reversed',
            automargin: true,
          },
        }}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
  );
}

interface SojournRow {
  activity: string;
  work_seconds: number;
  wait_seconds: number;
  n: number;
}

function SojournVsOwn({ data }: { data: { rows: SojournRow[] } }) {
  if (!data.rows || data.rows.length === 0) {
    return <Empty description="Нет данных для построения" />;
  }
  const activities = data.rows.map((r) => r.activity);
  const work = {
    x: activities,
    y: data.rows.map((r) => r.work_seconds),
    name: 'Работа',
    type: 'bar',
    marker: { color: '#1677ff' },
    hovertemplate: '%{x}<br>Работа: %{y:.0f} сек<extra></extra>',
  };
  const wait = {
    x: activities,
    y: data.rows.map((r) => r.wait_seconds),
    name: 'Ожидание',
    type: 'bar',
    marker: { color: '#fa8c16' },
    hovertemplate: '%{x}<br>Ожидание: %{y:.0f} сек<extra></extra>',
  };
  return (
    <PlotBox>
      <Plot
        data={[work, wait] as Data[]}
        layout={{
          ...BASE_LAYOUT,
          margin: { l: 64, r: 16, t: 16, b: 120 },
          barmode: 'stack',
          showlegend: true,
          legend: { orientation: 'h' },
          yaxis: { title: { text: 'Длительность (сек)' } },
          // Полное имя — в hovertemplate, подпись по оси обрезается.
          xaxis: {
            tickmode: 'array',
            tickvals: activities,
            ticktext: activities.map((n) => truncateLabel(n, 24)),
            tickangle: -30,
            automargin: true,
          },
        }}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </PlotBox>
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
      return <div className="gpc-kpi" title={kpi.formatted}>{kpi.formatted}</div>;
    }
    case 'bar_chart':
      return <BarOrLine data={data as never} mode="bar" />;
    case 'line_chart':
      return <BarOrLine data={data as never} mode="line" />;
    case 'monthly_dynamics':
      return <MonthlyDynamics data={data as never} />;
    case 'operations_dynamics':
      return <OperationsDynamics data={data as never} />;
    case 'events_per_case_histogram':
      return <EventsPerCaseHistogram data={data as never} />;
    case 'case_flow_cumulative':
      return <CaseFlow data={data as never} />;
    case 'operations_summary_short':
      return <OperationsSummaryShort data={data as never} />;
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
    case 'operation_durations_boxplot':
      return <OperationDurationsBoxplot data={data as never} />;
    case 'case_duration_cdf':
      return <CaseDurationCdf data={data as never} />;
    case 'duration_bottleneck_heatmap':
      return <DurationBottleneckHeatmap data={data as never} />;
    case 'sojourn_vs_own':
      return <SojournVsOwn data={data as never} />;
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
