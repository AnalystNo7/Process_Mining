import { useQuery } from '@tanstack/react-query';
import { Table, type TableColumnsType } from 'antd';
import { useState } from 'react';

import { listEvents, type EventFilter, type RawEventRow } from '@/api/analytics';
import { formatDateTime, formatDuration } from '@/lib/format';

const PAGE_SIZE = 100;

/**
 * T44: подвкладка «Детали → Датасет» — постраничный список сырых событий
 * лога с серверной пагинацией. Используется внутри дашборда (DashboardTabs),
 * фильтры приходят из глобальных фильтров дашборда.
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
  const filterKey = JSON.stringify(externalFilter ?? {});

  const { data, isLoading } = useQuery({
    queryKey: ['events', projectId, vdId, page, filterKey],
    queryFn: () =>
      listEvents(projectId, vdId, {
        page,
        page_size: PAGE_SIZE,
        filters: externalFilter,
      }),
  });

  const columns: TableColumnsType<RawEventRow> = [
    { title: 'ID кейса', dataIndex: 'case_id', key: 'case_id', width: 160 },
    { title: 'Операция', dataIndex: 'activity', key: 'activity' },
    {
      title: 'Начало',
      dataIndex: 'timestamp_start',
      key: 'timestamp_start',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Окончание',
      dataIndex: 'timestamp_end',
      key: 'timestamp_end',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Длительность',
      dataIndex: 'own_duration_seconds',
      key: 'own_duration_seconds',
      width: 150,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Исполнитель',
      dataIndex: 'resource',
      key: 'resource',
      render: (value: string | null) => value ?? '—',
    },
    {
      title: 'Подразделение',
      dataIndex: 'department',
      key: 'department',
      render: (value: string | null) => value ?? '—',
    },
  ];

  return (
    <Table
      rowKey={(_, index) => String((page - 1) * PAGE_SIZE + (index ?? 0))}
      loading={isLoading}
      columns={columns}
      dataSource={data?.items ?? []}
      size="small"
      pagination={{
        current: page,
        pageSize: PAGE_SIZE,
        total: data?.total ?? 0,
        showSizeChanger: false,
        showTotal: (total) => `Всего событий: ${total}`,
        onChange: setPage,
      }}
      scroll={{ x: true }}
    />
  );
}
