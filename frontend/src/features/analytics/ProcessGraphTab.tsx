import { DownloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Empty, Select, Slider, Space, Spin, Typography } from 'antd';
import { useState } from 'react';

import { downloadBpmn, getDfg } from '@/api/analytics';
import { ProcessGraph } from '@/components/ProcessGraph';
import { getErrorMessage, notifyError } from '@/lib/notify';

const NODE_LIMITS = [
  { value: 40, label: '40 операций' },
  { value: 60, label: '60 операций' },
  { value: 100, label: '100 операций' },
  { value: 200, label: '200 операций' },
];

const ACTIVITY_LEVELS = [
  { value: 'raw', label: 'Операции' },
  { value: 'role', label: 'Операции с ролями' },
];

export function ProcessGraphTab({
  projectId,
  vdId,
  vdName,
}: {
  projectId: number;
  vdId: number;
  vdName: string;
}) {
  const [minEdge, setMinEdge] = useState(0);
  const [maxNodes, setMaxNodes] = useState(60);
  const [activityLevel, setActivityLevel] = useState('raw');

  const { data, isLoading } = useQuery({
    queryKey: ['dfg', projectId, vdId, minEdge, maxNodes, activityLevel],
    queryFn: () =>
      getDfg(projectId, vdId, {
        min_edge_frequency_pct: minEdge,
        max_nodes: maxNodes,
        activity_level: activityLevel,
      }),
  });

  const bpmnMutation = useMutation({
    mutationFn: () => downloadBpmn(projectId, vdId, `${vdName}.bpmn`),
    onError: (error) =>
      notifyError(getErrorMessage(error, 'Не удалось экспортировать BPMN')),
  });

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap size="large">
        <Space>
          <Typography.Text type="secondary">Детализация:</Typography.Text>
          <Select
            value={activityLevel}
            onChange={setActivityLevel}
            options={ACTIVITY_LEVELS}
            style={{ width: 200 }}
          />
        </Space>
        <Space>
          <Typography.Text type="secondary">Узлов на графе:</Typography.Text>
          <Select
            value={maxNodes}
            onChange={setMaxNodes}
            options={NODE_LIMITS}
            style={{ width: 160 }}
          />
        </Space>
        <Space>
          <Typography.Text type="secondary">Порог частоты рёбер:</Typography.Text>
          <Slider
            min={0}
            max={50}
            value={minEdge}
            onChange={setMinEdge}
            style={{ width: 160 }}
            tooltip={{ formatter: (value) => `${value}%` }}
          />
        </Space>
        <Button
          icon={<DownloadOutlined />}
          loading={bpmnMutation.isPending}
          onClick={() => bpmnMutation.mutate()}
        >
          Экспорт BPMN
        </Button>
      </Space>

      <Typography.Paragraph type="secondary">
        На графе показаны самые частые операции (топ-{maxNodes}). Полный процесс
        содержит сотни операций — для читаемости отображается срез.
      </Typography.Paragraph>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : !data || data.nodes.length === 0 ? (
        <Empty description="Недостаточно данных для построения графа" />
      ) : (
        <ProcessGraph nodes={data.nodes} edges={data.edges} />
      )}
    </div>
  );
}
