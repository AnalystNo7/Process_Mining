import { useQuery } from '@tanstack/react-query';
import { Table, type TableColumnsType, type TablePaginationConfig } from 'antd';
import type {
  FilterValue,
  SorterResult,
} from 'antd/es/table/interface';
import { useState } from 'react';

import { listEvents, type EventFilter, type RawEventRow } from '@/api/analytics';
import { formatDateTime, formatDuration } from '@/lib/format';
import {
  DEFAULT_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS_STR,
  TWO_STATE_SORT_DIRECTIONS,
} from '@/lib/table';

/** T49: ключ колонки AntD → поле сортировки на бэке. */
const SORT_COLUMN_TO_FIELD: Record<string, string> = {
  case_id: 'case_id',
  activity: 'activity',
  timestamp_start: 'timestamp_start',
  timestamp_end: 'timestamp_end',
  own_duration_seconds: 'own_duration_seconds',
  resource: 'resource',
  department: 'department',
};

/**
 * T44/T49: подвкладка «Детали → Датасет» — постраничный список сырых событий
 * лога с серверной пагинацией и сортировкой по любому столбцу. Используется
 * внутри дашборда (DashboardTabs), фильтры приходят из глобальных фильтров.
 */
export function DatasetTab({
  projectId,
  vdId,
  externalFilter,
}: {
  projectId: number;
  vdId: number;
  externalFilter?: EventFilter;
}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const filterKey = JSON.stringify(externalFilter ?? {});

  const { data, isLoading } = useQuery({
    queryKey: [
      'events', projectId, vdId, page, pageSize, sortBy, sortOrder, filterKey,
    ],
    queryFn: () =>
      listEvents(projectId, vdId, {
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
    sorter: SorterResult<RawEventRow> | SorterResult<RawEventRow>[],
  ) => {
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

  const columns: TableColumnsType<RawEventRow> = [
    { title: 'ID кейса', dataIndex: 'case_id', key: 'case_id', width: 160, sorter: true },
    { title: 'Операция', dataIndex: 'activity', key: 'activity', sorter: true },
    {
      title: 'Начало',
      dataIndex: 'timestamp_start',
      key: 'timestamp_start',
      sorter: true,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Окончание',
      dataIndex: 'timestamp_end',
      key: 'timestamp_end',
      sorter: true,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Длительность',
      dataIndex: 'own_duration_seconds',
      key: 'own_duration_seconds',
      width: 150,
      sorter: true,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Исполнитель',
      dataIndex: 'resource',
      key: 'resource',
      sorter: true,
      render: (value: string | null) => value ?? '—',
    },
    {
      title: 'Подразделение',
      dataIndex: 'department',
      key: 'department',
      sorter: true,
      render: (value: string | null) => value ?? '—',
    },
  ];

  return (
    <Table
      rowKey={(_, index) => String((page - 1) * pageSize + (index ?? 0))}
      loading={isLoading}
      columns={columns}
      dataSource={data?.items ?? []}
      size="small"
      onChange={handleTableChange}
      sortDirections={TWO_STATE_SORT_DIRECTIONS}
      pagination={{
        current: page,
        pageSize,
        total: data?.total ?? 0,
        showSizeChanger: true,
        pageSizeOptions: TABLE_PAGE_SIZE_OPTIONS_STR,
        showTotal: (total) => `Всего событий: ${total}`,
      }}
      scroll={{ x: true }}
    />
  );
}
