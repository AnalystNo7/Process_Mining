import { useQuery } from '@tanstack/react-query';
import {
  Button,
  Descriptions,
  Drawer,
  Space,
  Table,
  Tag,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';

import {
  getCaseDetail,
  listCases,
  type CaseEvent,
  type CaseSummary,
  type EventFilter,
} from '@/api/analytics';
import { formatDateTime, formatDuration } from '@/lib/format';

const PAGE_SIZE = 50;

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
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);

  const filterKey = JSON.stringify(externalFilter ?? {});

  const { data, isLoading } = useQuery({
    queryKey: ['cases', projectId, vdId, page, filterKey],
    queryFn: () =>
      listCases(projectId, vdId, {
        page,
        page_size: PAGE_SIZE,
        filters: externalFilter,
      }),
  });

  const columns: TableColumnsType<CaseSummary> = [
    {
      title: 'ID кейса',
      key: 'case_id',
      render: (_, row) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => setOpenCaseId(row.case_id)}>
          {row.case_id}
        </Button>
      ),
    },
    { title: 'Операций', dataIndex: 'n_events', key: 'n_events', width: 100 },
    {
      title: 'Длительность',
      dataIndex: 'duration_seconds',
      key: 'duration',
      width: 160,
      render: (value: number) => formatDuration(value),
    },
    {
      title: 'Переделки',
      dataIndex: 'has_rework',
      key: 'has_rework',
      width: 120,
      render: (value: boolean) =>
        value ? <Tag color="orange">Есть</Tag> : <Tag color="green">Нет</Tag>,
    },
    {
      title: 'Начало',
      dataIndex: 'start',
      key: 'start',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Окончание',
      dataIndex: 'end',
      key: 'end',
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
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: data?.total ?? 0,
          showSizeChanger: false,
          onChange: setPage,
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
        <Descriptions.Item label="Переделки">
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
