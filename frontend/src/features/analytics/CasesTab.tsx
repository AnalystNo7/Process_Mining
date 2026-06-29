import { useQuery } from '@tanstack/react-query';
import {
  Button,
  Descriptions,
  Drawer,
  Space,
  Table,
  Tag,
  type TableColumnsType,
  type TablePaginationConfig,
} from 'antd';
import type {
  FilterValue,
  SorterResult,
} from 'antd/es/table/interface';
import { useState } from 'react';

import {
  getCaseDetail,
  listCases,
  type CaseEvent,
  type CaseSummary,
  type EventFilter,
} from '@/api/analytics';
import { formatDateTime, formatDuration } from '@/lib/format';
import {
  DEFAULT_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS_STR,
  TWO_STATE_SORT_DIRECTIONS,
} from '@/lib/table';

/** Сопоставление колонок AntD ↔ полей сортировки на бэке (T49). */
const SORT_COLUMN_TO_FIELD: Record<string, string> = {
  case_id: 'case_id',
  n_events: 'n_events',
  duration: 'duration_seconds',
  has_rework: 'has_rework',
  start: 'start',
  end: 'end',
};

export function CasesTab({
  projectId,
  vdId,
  externalFilter,
}: {
  projectId: number;
  vdId: number;
  /** T44: фильтры из дашборда (при встраивании в подвкладку details.cases). */
  externalFilter?: EventFilter;
}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);

  const filterKey = JSON.stringify(externalFilter ?? {});

  const { data, isLoading } = useQuery({
    queryKey: [
      'cases', projectId, vdId, page, pageSize, sortBy, sortOrder, filterKey,
    ],
    queryFn: () =>
      listCases(projectId, vdId, {
        page,
        page_size: pageSize,
        filters: externalFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
  });

  const handleTableChange = (
    pagination: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<CaseSummary> | SorterResult<CaseSummary>[],
  ) => {
    // Сортировка (одиночная) — берём первый sorter.
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const colKey = s?.columnKey ? String(s.columnKey) : undefined;
    const nextSortBy = colKey ? SORT_COLUMN_TO_FIELD[colKey] : undefined;
    const nextOrder: 'asc' | 'desc' =
      s?.order === 'ascend' ? 'asc' : s?.order === 'descend' ? 'desc' : 'desc';
    const sortChanged = nextSortBy !== sortBy || nextOrder !== sortOrder;
    if (sortChanged) {
      setSortBy(s?.order ? nextSortBy : undefined);
      setSortOrder(nextOrder);
      setPage(1);
    }
    if (pagination.current && pagination.current !== page) setPage(pagination.current);
    if (pagination.pageSize && pagination.pageSize !== pageSize) {
      setPageSize(pagination.pageSize);
      setPage(1);
    }
  };

  const columns: TableColumnsType<CaseSummary> = [
    {
      title: 'ID кейса',
      key: 'case_id',
      sorter: true,
      render: (_, row) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => setOpenCaseId(row.case_id)}>
          {row.case_id}
        </Button>
      ),
    },
    {
      title: 'Операций',
      dataIndex: 'n_events',
      key: 'n_events',
      width: 100,
      sorter: true,
    },
    {
      title: 'Длительность',
      dataIndex: 'duration_seconds',
      key: 'duration',
      width: 160,
      sorter: true,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Повторы',
      dataIndex: 'has_rework',
      key: 'has_rework',
      width: 120,
      sorter: true,
      render: (value: boolean) =>
        value ? <Tag color="orange">Есть</Tag> : <Tag color="green">Нет</Tag>,
    },
    {
      title: 'Начало',
      dataIndex: 'start',
      key: 'start',
      sorter: true,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Окончание',
      dataIndex: 'end',
      key: 'end',
      sorter: true,
      render: (value: string) => formatDateTime(value),
    },
  ];

  return (
    <div>
      <Table
        rowKey="case_id"
        loading={isLoading}
        columns={columns}
        dataSource={data?.items ?? []}
        onChange={handleTableChange}
        sortDirections={TWO_STATE_SORT_DIRECTIONS}
        pagination={{
          current: page,
          pageSize,
          total: data?.total ?? 0,
          showSizeChanger: true,
          pageSizeOptions: TABLE_PAGE_SIZE_OPTIONS_STR,
        }}
      />
      <Drawer
        title={`Кейс ${openCaseId ?? ''}`}
        open={openCaseId != null}
        onClose={() => setOpenCaseId(null)}
        width={680}
      >
        {openCaseId && (
          <CaseDetailView projectId={projectId} vdId={vdId} caseId={openCaseId} />
        )}
      </Drawer>
    </div>
  );
}

function CaseDetailView({
  projectId,
  vdId,
  caseId,
}: {
  projectId: number;
  vdId: number;
  caseId: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['case', projectId, vdId, caseId],
    queryFn: () => getCaseDetail(projectId, vdId, caseId),
  });

  const columns: TableColumnsType<CaseEvent> = [
    {
      title: 'Операция',
      key: 'activity',
      render: (_, event) => (
        <Space size={4}>
          {event.activity}
          {event.is_repeat && <Tag color="orange">повтор</Tag>}
        </Space>
      ),
    },
    {
      title: 'Начало',
      dataIndex: 'timestamp_start',
      key: 'timestamp_start',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Длительность с переходом',
      dataIndex: 'sojourn_seconds',
      key: 'sojourn',
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Исполнитель',
      dataIndex: 'resource',
      key: 'resource',
      render: (value: string | null) => value ?? '—',
    },
  ];

  return (
    <div>
      <Descriptions size="small" column={1} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="Операций">{data?.n_events ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="Общая длительность">
          {formatDuration(data?.total_duration_seconds)}
        </Descriptions.Item>
        <Descriptions.Item label="Повторы">
          {data?.has_rework ? 'Есть' : 'Нет'}
        </Descriptions.Item>
      </Descriptions>
      <Table
        rowKey={(_, index) => String(index)}
        loading={isLoading}
        size="small"
        columns={columns}
        dataSource={data?.events ?? []}
        pagination={false}
      />
    </div>
  );
}
