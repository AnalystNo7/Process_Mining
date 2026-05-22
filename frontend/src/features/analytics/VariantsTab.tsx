import { useQuery } from '@tanstack/react-query';
import {
  InputNumber,
  Space,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';

import { getTopPaths, type VariantRow } from '@/api/analytics';
import { formatDuration } from '@/lib/format';

export function VariantsTab({
  projectId,
  vdId,
}: {
  projectId: number;
  vdId: number;
}) {
  const [topN, setTopN] = useState(10);

  const { data, isLoading } = useQuery({
    queryKey: ['top-paths', projectId, vdId, topN],
    queryFn: () => getTopPaths(projectId, vdId, topN),
  });

  const columns: TableColumnsType<VariantRow> = [
    {
      title: '#',
      key: 'index',
      width: 48,
      render: (_, __, index) => index + 1,
    },
    {
      title: 'Маршрут',
      key: 'trace',
      render: (_, row) => row.trace.join(' → '),
    },
    { title: 'Кейсов', dataIndex: 'n_cases', key: 'n_cases', width: 100 },
    {
      title: 'Ср. длительность',
      dataIndex: 'avg_duration_seconds',
      key: 'avg',
      width: 160,
      render: (value: number) => formatDuration(value),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Typography.Text type="secondary">Показать вариантов:</Typography.Text>
        <InputNumber
          min={1}
          max={50}
          value={topN}
          onChange={(value) => setTopN(value ?? 10)}
        />
        {data && (
          <>
            <Tag>Всего кейсов: {data.total_cases}</Tag>
            <Tag>Всего вариантов: {data.total_variants}</Tag>
            <Tag color="blue">Покрытие топ-{data.top_n}: {data.coverage_pct.toFixed(1)}%</Tag>
          </>
        )}
      </Space>
      <Table
        rowKey={(_, index) => String(index)}
        loading={isLoading}
        columns={columns}
        dataSource={data?.variants ?? []}
        pagination={false}
      />
    </div>
  );
}
