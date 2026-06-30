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

import { durationPlotHeight } from './durationLayout';

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

// Блок фиксированной (адаптивной) высоты для виджетов длительности: график
// получает явную высоту под число операций; при превышении карточки тело
// карточки (overflow:auto) скроллит. flexShrink:0 — не даём flex сжать его.
function TallPlotBox({
  height,
  children,
}: {
  height: number;
  children: React.ReactNode;
}) {
  return <div style={{ width: '100%', height, flexShrink: 0 }}>{children}</div>;
}

/** Обрезает длинную подпись до max символов с многоточием. Полное имя
 * показывается в подсказке (hover) — см. виджеты длительности. */
function truncateLabel(s: string, max = 32): string {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

/** Равномерные засечки 0..maxValue (сек) с человекочитаемыми подписями.
 * Заменяет сырые секунды на оси д/ч/м/с. */
function durationTicks(
  maxValue: number,
  count = 6,
): { tickvals: number[]; ticktext: string[] } {
  const top = maxValue > 0 ? maxValue : 1;
  const tickvals = Array.from({ length: count }, (_, i) => (top * i) / (count - 1));
  return { tickvals, ticktext: tickvals.map((v) => formatDuration(v)) };
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
      title: '% повторов',
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
        Глобальный уровень повторов: {data.global_rework_pct.toFixed(2)}%
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
  // Нативный hover ящика и сырые точки-выбросы отключены (boxpoints:false,
  // hoverinfo:skip), т.к. Plotly показал бы значения как «300к» секунд.
  // Вместо них — два scatter-слоя ниже с подсказками в д/ч/м/с.
  // Горизонтальная ориентация: операции по оси Y, длительность по X — при
  // многих операциях карточка растёт в высоту, имена не налезают.
  const boxTraces = data.traces.map((tr) => ({
    type: 'box',
    name: tr.name,
    x: tr.y,
    orientation: 'h',
    boxmean: true,
    boxpoints: false,
    hoverinfo: 'skip',
    marker: { color: '#1677ff' },
    line: { color: '#1677ff' },
  }));
  // Слой сводки: маркер у медианы каждой операции с полной подсказкой.
  const summaryTrace = {
    type: 'scatter',
    mode: 'markers',
    x: data.traces.map((tr) => tr.median),
    y: data.traces.map((tr) => tr.name),
    marker: { color: '#1677ff', size: 12, symbol: 'line-ns-open' },
    customdata: data.traces.map((tr) => [
      formatDuration(tr.median),
      formatDuration(tr.mean),
      formatDuration(tr.q1),
      formatDuration(tr.q3),
      formatDuration(tr.min),
      formatDuration(tr.max),
      tr.n,
    ]),
    hovertemplate:
      '%{y}<br>медиана: %{customdata[0]}<br>среднее: %{customdata[1]}' +
      '<br>Q1–Q3: %{customdata[2]} – %{customdata[3]}' +
      '<br>мин–макс: %{customdata[4]} – %{customdata[5]}' +
      '<br>событий: %{customdata[6]}<extra></extra>',
    showlegend: false,
  };
  // Слой выбросов: точки за оградой [q1−1.5·IQR, q3+1.5·IQR], hover в д/ч/м/с.
  // Горизонтально: x = значение, y = имя операции.
  const outX: number[] = [];
  const outY: string[] = [];
  const outText: string[] = [];
  data.traces.forEach((tr) => {
    const iqr = tr.q3 - tr.q1;
    const lo = tr.q1 - 1.5 * iqr;
    const hi = tr.q3 + 1.5 * iqr;
    tr.y.forEach((v) => {
      if (v < lo || v > hi) {
        outX.push(v);
        outY.push(tr.name);
        outText.push(formatDuration(v));
      }
    });
  });
  const outlierTrace = {
    type: 'scatter',
    mode: 'markers',
    x: outX,
    y: outY,
    marker: { color: 'rgba(22,119,255,0.45)', size: 5 },
    customdata: outText,
    hovertemplate: 'выброс: %{customdata}<extra></extra>',
    showlegend: false,
  };
  const traces = [...boxTraces, summaryTrace, outlierTrace];
  const names = data.traces.map((tr) => tr.name);
  const maxVal = Math.max(
    1,
    ...data.traces.flatMap((tr) => (tr.y.length ? tr.y : [0])),
  );
  const xTicks = durationTicks(maxVal);
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    margin: { l: 200, r: 16, t: 16, b: 48 },
    showlegend: false,
    // Ось длительности — снизу (X); операции — слева (Y).
    xaxis: {
      title: { text: 'Длительность' },
      tickmode: 'array',
      tickvals: xTicks.tickvals,
      ticktext: xTicks.ticktext,
    },
    // Полное имя операции остаётся в name (видно в hover), подпись слева
    // обрезается, чтобы длинные названия помещались.
    yaxis: {
      tickmode: 'array',
      tickvals: names,
      ticktext: names.map((n) => truncateLabel(n, 28)),
      automargin: true,
    },
  };
  return (
    <TallPlotBox
      height={durationPlotHeight('operation_durations_boxplot', names.length)}
    >
      <Plot
        data={traces as Data[]}
        layout={layout}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </TallPlotBox>
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
  const xs = data.points.map((p) => p.x);
  const trace = {
    x: xs,
    y: data.points.map((p) => p.y),
    type: 'scatter',
    mode: 'lines',
    line: { color: '#1677ff', shape: 'hv' },
    customdata: xs.map((v) => formatDuration(v)),
    hovertemplate: '%{y:.1f}% ≤ %{customdata}<extra></extra>',
  };
  const xTicks = durationTicks(Math.max(1, ...xs));
  const layout: Partial<Layout> = {
    ...BASE_LAYOUT,
    yaxis: { title: { text: data.y_label }, range: [0, 100] },
    xaxis: {
      title: { text: 'Длительность' },
      tickmode: 'array',
      tickvals: xTicks.tickvals,
      ticktext: xTicks.ticktext,
    },
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
    cells: {
      x: string;
      y: string;
      value: number;
      median: number;
      mean: number;
      n: number;
    }[];
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
  // полное имя и статистики (медиана/среднее/n) — в подсказке.
  const ys = data.y_categories;
  const xs = data.x_categories;
  const lookup = new Map(data.cells.map((c) => [`${c.x}|${c.y}`, c]));
  const z = ys.map((y) => xs.map((x) => lookup.get(`${x}|${y}`)?.value ?? null));
  const text = ys.map((y) =>
    xs.map((x) => {
      const c = lookup.get(`${x}|${y}`);
      return c == null
        ? ''
        : `${y}<br>${x}<br>медиана: ${formatDuration(c.median)}` +
            `<br>среднее: ${formatDuration(c.mean)}<br>событий: ${c.n}`;
    }),
  );
  // Шкала цвета в человекочитаемых единицах: 4 равномерные засечки.
  const vals = data.cells.map((c) => c.value);
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  const tickvals = [0, 1, 2, 3].map((i) => mn + ((mx - mn) * i) / 3);
  return (
    <TallPlotBox
      height={durationPlotHeight('duration_bottleneck_heatmap', ys.length)}
    >
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
            ticktext: xs.map((s) => truncateLabel(s, 28)),
            tickangle: -45,
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
    </TallPlotBox>
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
  // Горизонтальная ориентация: операции по Y, длительность по X — при многих
  // операциях карточка растёт в высоту, имена не налезают.
  const work = {
    y: activities,
    x: data.rows.map((r) => r.work_seconds),
    name: 'Работа',
    type: 'bar',
    orientation: 'h',
    marker: { color: '#1677ff' },
    customdata: data.rows.map((r) => formatDuration(r.work_seconds)),
    hovertemplate: '%{y}<br>Работа: %{customdata}<extra></extra>',
  };
  const wait = {
    y: activities,
    x: data.rows.map((r) => r.wait_seconds),
    name: 'Ожидание',
    type: 'bar',
    orientation: 'h',
    marker: { color: '#fa8c16' },
    customdata: data.rows.map((r) => formatDuration(r.wait_seconds)),
    hovertemplate: '%{y}<br>Ожидание: %{customdata}<extra></extra>',
  };
  const maxTotal = Math.max(
    1,
    ...data.rows.map((r) => r.work_seconds + r.wait_seconds),
  );
  const xTicks = durationTicks(maxTotal);
  return (
    <TallPlotBox height={durationPlotHeight('sojourn_vs_own', activities.length)}>
      <Plot
        data={[work, wait] as Data[]}
        layout={{
          ...BASE_LAYOUT,
          margin: { l: 200, r: 16, t: 16, b: 48 },
          barmode: 'stack',
          showlegend: true,
          legend: { orientation: 'h' },
          xaxis: {
            title: { text: 'Длительность' },
            tickmode: 'array',
            tickvals: xTicks.tickvals,
            ticktext: xTicks.ticktext,
          },
          // Полное имя — в hovertemplate, подпись слева обрезается.
          yaxis: {
            tickmode: 'array',
            tickvals: activities,
            ticktext: activities.map((n) => truncateLabel(n, 28)),
            automargin: true,
          },
        }}
        style={PLOT_STYLE}
        config={PLOT_CONFIG}
        useResizeHandler
      />
    </TallPlotBox>
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
