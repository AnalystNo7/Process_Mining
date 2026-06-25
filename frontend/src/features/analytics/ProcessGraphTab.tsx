import { CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Button,
  Card,
  Checkbox,
  Empty,
  List,
  message,
  Select,
  Slider,
  Space,
  Spin,
  Table,
  Tooltip,
  Typography,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';

import {
  downloadBpmn,
  getFilterOptions,
  getMonthlyDynamics,
  getOperations,
  getProcessMap,
} from '@/api/analytics';
import type { EventFilter, OperationSummaryRow } from '@/api/analytics';
import { Plot } from '@/components/Plot';
import { ProcessGraph } from '@/components/ProcessGraph';
import type { GraphHighlight } from '@/components/ProcessGraph';
import { FilterPanel } from '@/features/analytics/FilterPanel';
import { formatDuration } from '@/lib/format';
import { getErrorMessage, notifyError } from '@/lib/notify';
import {
  DEFAULT_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS_STR,
  TWO_STATE_SORT_DIRECTIONS,
} from '@/lib/table';

const START = '__start__';
const END = '__end__';

const ACTIVITY_LEVELS = [
  { value: 'raw', label: 'Операции' },
  { value: 'role', label: 'Операции с ролями' },
];

const N_OPTIONS = [3, 5, 8, 10, 15, 20, 30].map((value) => ({
  value,
  label: `Топ-${value} путей`,
}));

const NODE_LIMITS = [40, 60, 100, 200].map((value) => ({
  value,
  label: `${value} операций`,
}));

export function ProcessGraphTab({
  projectId,
  vdId,
  vdName,
  embedded = false,
  externalFilter,
}: {
  projectId: number;
  vdId: number;
  vdName: string;
  /** T47: при `embedded=true` компонент рендерится внутри дашборда — без
   * собственной FilterPanel, фильтры приходят извне (externalFilter). */
  embedded?: boolean;
  externalFilter?: EventFilter;
}) {
  const [localFilters, setLocalFilters] = useState<EventFilter>({});
  // В embedded-режиме игнорируем локальный state и берём фильтры от родителя.
  // useMemo — чтобы ссылка на объект не менялась каждый рендер (стабильные deps).
  const filters = useMemo<EventFilter>(
    () => (embedded ? (externalFilter ?? {}) : localFilters),
    [embedded, externalFilter, localFilters],
  );
  const [mode, setMode] = useState<'top_paths' | 'frequency'>('top_paths');
  const [activityLevel, setActivityLevel] = useState('raw');
  const [n, setN] = useState(5);
  const [minEdge, setMinEdge] = useState(0);
  const [maxNodes, setMaxNodes] = useState(60);
  const [selectedPaths, setSelectedPaths] = useState<number[]>([]);
  const [crossFilterOn, setCrossFilterOn] = useState(false);

  const filtersKey = JSON.stringify(filters);

  useEffect(() => {
    setSelectedPaths([]);
  }, [filtersKey, n, activityLevel]);

  const optionsQuery = useQuery({
    queryKey: ['filter-options', projectId, vdId],
    queryFn: () => getFilterOptions(projectId, vdId),
  });

  const pathsQuery = useQuery({
    queryKey: ['process-paths', projectId, vdId, n, activityLevel, filtersKey],
    queryFn: () =>
      getProcessMap(projectId, vdId, {
        mode: 'top_paths',
        n,
        activity_level: activityLevel,
        filters,
      }),
  });

  const paths = useMemo(
    () => pathsQuery.data?.paths ?? [],
    [pathsQuery.data]
  );

  const effectiveFilters = useMemo<EventFilter>(() => {
    if (!crossFilterOn || selectedPaths.length === 0) {
      return filters;
    }
    const ids = new Set<string>();
    for (const idx of selectedPaths) {
      paths[idx]?.case_ids.forEach((caseId) => ids.add(caseId));
    }
    return ids.size > 0 ? { ...filters, case_ids: [...ids] } : filters;
  }, [crossFilterOn, selectedPaths, paths, filters]);

  const effectiveKey = JSON.stringify(effectiveFilters);

  const mapQuery = useQuery({
    queryKey: [
      'process-map',
      projectId,
      vdId,
      mode,
      n,
      activityLevel,
      minEdge,
      maxNodes,
      effectiveKey,
    ],
    queryFn: () =>
      getProcessMap(projectId, vdId, {
        mode,
        n,
        activity_level: activityLevel,
        min_edge_frequency_pct: minEdge,
        max_nodes: maxNodes,
        filters: effectiveFilters,
      }),
  });

  const operationsQuery = useQuery({
    queryKey: ['process-operations', projectId, vdId, activityLevel, effectiveKey],
    queryFn: () =>
      getOperations(projectId, vdId, {
        activity_level: activityLevel,
        filters: effectiveFilters,
      }),
  });

  const dynamicsQuery = useQuery({
    queryKey: ['process-dynamics', projectId, vdId, effectiveKey],
    queryFn: () => getMonthlyDynamics(projectId, vdId, { filters: effectiveFilters }),
  });

  const bpmnMutation = useMutation({
    mutationFn: () => downloadBpmn(projectId, vdId, `${vdName}.bpmn`),
    onError: (error) =>
      notifyError(getErrorMessage(error, 'Не удалось экспортировать BPMN')),
  });

  const highlight = useMemo<GraphHighlight | undefined>(() => {
    if (crossFilterOn || selectedPaths.length === 0) {
      return undefined;
    }
    const nodeIds = new Set<string>([START, END]);
    const edgeKeys = new Set<string>();
    for (const idx of selectedPaths) {
      const trace = paths[idx]?.trace ?? [];
      if (trace.length === 0) {
        continue;
      }
      trace.forEach((activity) => nodeIds.add(activity));
      const sequence = [START, ...trace, END];
      for (let i = 0; i < sequence.length - 1; i += 1) {
        edgeKeys.add(`${sequence[i]}->${sequence[i + 1]}`);
      }
    }
    return { nodeIds: [...nodeIds], edgeKeys: [...edgeKeys] };
  }, [crossFilterOn, selectedPaths, paths]);

  const togglePath = (index: number) => {
    setSelectedPaths((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const mapData = mapQuery.data;
  const operations = operationsQuery.data?.items ?? [];
  const maxEvents = Math.max(1, ...operations.map((row) => row.n_events));
  const dynamics = dynamicsQuery.data?.items ?? [];

  const operationColumns = [
    {
      title: 'Операция',
      dataIndex: 'activity',
      key: 'activity',
      ellipsis: true,
      sorter: (a: OperationSummaryRow, b: OperationSummaryRow) =>
        a.activity.localeCompare(b.activity, 'ru'),
    },
    {
      title: 'Кол-во экземпляров',
      dataIndex: 'n_cases',
      key: 'n_cases',
      width: 110,
      sorter: (a: OperationSummaryRow, b: OperationSummaryRow) => a.n_cases - b.n_cases,
    },
    {
      title: 'Кол-во операций',
      dataIndex: 'n_events',
      key: 'n_events',
      width: 130,
      sorter: (a: OperationSummaryRow, b: OperationSummaryRow) => a.n_events - b.n_events,
      render: (value: number) => (
        <div style={{ position: 'relative', minWidth: 90 }}>
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: `${(value / maxEvents) * 100}%`,
              background: '#e6f4ff',
              borderRadius: 2,
            }}
          />
          <span style={{ position: 'relative' }}>{value}</span>
        </div>
      ),
    },
    {
      title: 't (avg)',
      dataIndex: 'avg_own_duration_seconds',
      key: 'avg',
      width: 110,
      sorter: (a: OperationSummaryRow, b: OperationSummaryRow) =>
        a.avg_own_duration_seconds - b.avg_own_duration_seconds,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 't (median)',
      dataIndex: 'median_own_duration_seconds',
      key: 'median',
      width: 110,
      sorter: (a: OperationSummaryRow, b: OperationSummaryRow) =>
        a.median_own_duration_seconds - b.median_own_duration_seconds,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'ср. доля в t экземпляра',
      dataIndex: 'avg_share_pct',
      key: 'share',
      width: 130,
      sorter: (a: OperationSummaryRow, b: OperationSummaryRow) =>
        a.avg_share_pct - b.avg_share_pct,
      render: (value: number) => `${value.toFixed(1)}%`,
    },
  ];

  const renderPathsTab = () => (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      <Space wrap>
        <Typography.Text type="secondary">Путей:</Typography.Text>
        <Select
          size="small"
          value={n}
          onChange={setN}
          options={N_OPTIONS}
          style={{ width: 140 }}
        />
      </Space>
      {pathsQuery.data && (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Показано {paths.length} из {pathsQuery.data.total_variants} путей · покрытие{' '}
          {pathsQuery.data.covered_cases} из {pathsQuery.data.total_cases} экз. (
          {pathsQuery.data.coverage_pct}%)
        </Typography.Text>
      )}
      <Checkbox
        checked={crossFilterOn}
        onChange={(event) => setCrossFilterOn(event.target.checked)}
      >
        Кросс-фильтр по выбранным путям
      </Checkbox>
      <List
        size="small"
        style={{ maxHeight: 380, overflow: 'auto' }}
        dataSource={paths}
        locale={{ emptyText: 'Нет путей' }}
        renderItem={(path) => {
          const selected = selectedPaths.includes(path.index);
          const handleCopyId = async (event: React.MouseEvent) => {
            event.stopPropagation();
            try {
              await navigator.clipboard.writeText(path.path_hash);
              void message.success(`ID пути скопирован: ${path.path_hash}`);
            } catch {
              void message.error('Не удалось скопировать в буфер обмена');
            }
          };
          return (
            <List.Item
              onClick={() => togglePath(path.index)}
              style={{
                cursor: 'pointer',
                background: selected ? '#e6f4ff' : undefined,
                paddingLeft: 8,
                paddingRight: 8,
              }}
            >
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Space>
                  <Checkbox checked={selected} />
                  <span>
                    <Typography.Text strong>Путь {path.index + 1}</Typography.Text>
                    <br />
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {path.trace.length} шагов · {path.n_cases} экз. ·{' '}
                      {formatDuration(path.avg_duration_seconds)}
                    </Typography.Text>
                  </span>
                </Space>
                <Tooltip title={`Скопировать ID: ${path.path_hash}`}>
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={handleCopyId}
                  />
                </Tooltip>
              </Space>
            </List.Item>
          );
        }}
      />
    </Space>
  );

  const renderFrequencyTab = () => (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Порог частоты рёбер
        </Typography.Text>
        <Slider
          min={0}
          max={50}
          value={minEdge}
          onChange={setMinEdge}
          tooltip={{ formatter: (value) => `${value}%` }}
        />
      </div>
      <div>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Узлов на графе
        </Typography.Text>
        <Select
          style={{ width: '100%', marginTop: 4 }}
          value={maxNodes}
          onChange={setMaxNodes}
          options={NODE_LIMITS}
        />
      </div>
      <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
        Частотный фильтр строит граф непосредственного следования по всем
        операциям с отсевом редких рёбер и лимитом узлов.
      </Typography.Paragraph>
    </Space>
  );

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      {!embedded && (
        <FilterPanel options={optionsQuery.data} onApply={setLocalFilters} />
      )}

      <div style={{ flex: 1, minWidth: 0 }}>
        <Space style={{ marginBottom: 16 }} wrap>
          <Typography.Text type="secondary">Детализация:</Typography.Text>
          <Select
            value={activityLevel}
            onChange={setActivityLevel}
            options={ACTIVITY_LEVELS}
            style={{ width: 200 }}
          />
          <Button
            icon={<DownloadOutlined />}
            loading={bpmnMutation.isPending}
            onClick={() => bpmnMutation.mutate()}
          >
            Экспорт BPMN
          </Button>
        </Space>

        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Card size="small" title="Количество операций и переходов">
              {mapQuery.isLoading ? (
                <div style={{ textAlign: 'center', padding: 48 }}>
                  <Spin size="large" />
                </div>
              ) : !mapData || mapData.nodes.length === 0 ? (
                <Empty description="Недостаточно данных для построения графа" />
              ) : (
                <ProcessGraph
                  nodes={mapData.nodes}
                  edges={mapData.edges}
                  highlight={highlight}
                />
              )}
            </Card>
          </div>

          <div style={{ width: 380, flexShrink: 0 }}>
            <Card
              size="small"
              tabList={[
                { key: 'top_paths', tab: 'Пути процесса' },
                { key: 'frequency', tab: 'Частотный фильтр' },
              ]}
              activeTabKey={mode}
              onTabChange={(key) => setMode(key as 'top_paths' | 'frequency')}
            >
              {mode === 'top_paths' ? renderPathsTab() : renderFrequencyTab()}
            </Card>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16, marginTop: 16, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Card size="small" title="Операции">
              <Table
                size="small"
                rowKey="activity"
                dataSource={operations}
                columns={operationColumns}
                loading={operationsQuery.isLoading}
                sortDirections={TWO_STATE_SORT_DIRECTIONS}
                pagination={{
                  defaultPageSize: DEFAULT_PAGE_SIZE,
                  showSizeChanger: true,
                  pageSizeOptions: TABLE_PAGE_SIZE_OPTIONS_STR,
                  hideOnSinglePage: true,
                }}
                scroll={{ x: true }}
              />
              <Typography.Paragraph
                type="secondary"
                style={{ fontSize: 11, marginTop: 8, marginBottom: 0 }}
              >
                t (avg) — средняя длительность операции; t (median) — медианная
                длительность; ср. доля в t экземпляра — средняя доля операции в
                длительности кейса.
              </Typography.Paragraph>
            </Card>
          </div>

          <div style={{ width: 480, flexShrink: 0 }}>
            <Card size="small" title="Динамика появления экземпляров">
              {dynamicsQuery.isLoading ? (
                <div style={{ textAlign: 'center', padding: 48 }}>
                  <Spin />
                </div>
              ) : dynamics.length === 0 ? (
                <Empty description="Нет данных" />
              ) : (
                <Plot
                  data={[
                    {
                      type: 'bar',
                      x: dynamics.map((row) => row.month),
                      y: dynamics.map((row) => row.n_cases),
                      marker: { color: '#1677ff' },
                      name: 'Кол-во экземпляров',
                    },
                  ]}
                  layout={{
                    height: 320,
                    margin: { l: 40, r: 16, t: 16, b: 40 },
                    xaxis: { title: { text: 'Дата начала экземпляра' } },
                    yaxis: { title: { text: 'Кол-во экземпляров' } },
                  }}
                  config={{ displaylogo: false, responsive: true }}
                  style={{ width: '100%' }}
                  useResizeHandler
                />
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
