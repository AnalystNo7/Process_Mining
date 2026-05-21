import { useQuery } from '@tanstack/react-query';
import {
  Input,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';

import { listAuditLog, type AuditEntry } from '@/api/audit';
import { formatDateTime } from '@/lib/format';

const PAGE_SIZE = 50;

export function AuditLogPage() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['audit-log', page, action],
    queryFn: () =>
      listAuditLog({
        page,
        page_size: PAGE_SIZE,
        action: action || undefined,
      }),
  });

  const columns: TableColumnsType<AuditEntry> = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Пользователь',
      key: 'user',
      render: (_, entry) => entry.user?.username ?? '—',
    },
    {
      title: 'Действие',
      dataIndex: 'action',
      key: 'action',
      render: (value: string) => <Tag>{value}</Tag>,
    },
    {
      title: 'Объект',
      key: 'entity',
      render: (_, entry) =>
        entry.entity_type ? `${entry.entity_type} #${entry.entity_id ?? '?'}` : '—',
    },
    {
      title: 'IP-адрес',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (value: string | null) => value ?? '—',
    },
  ];

  return (
    <div>
      <Typography.Title level={3}>Журнал действий</Typography.Title>
      <Input.Search
        placeholder="Фильтр по действию (например, project.create)"
        allowClear
        style={{ maxWidth: 360, marginBottom: 16 }}
        onSearch={(value) => {
          setPage(1);
          setAction(value.trim());
        }}
      />
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data?.items ?? []}
        expandable={{
          expandedRowRender: (entry) => (
            <pre style={{ margin: 0 }}>
              {JSON.stringify(entry.metadata ?? {}, null, 2)}
            </pre>
          ),
          rowExpandable: (entry) => entry.metadata != null,
        }}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: data?.total ?? 0,
          showSizeChanger: false,
          onChange: setPage,
        }}
      />
    </div>
  );
}
