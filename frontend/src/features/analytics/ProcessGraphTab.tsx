import { DownloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Empty, Slider, Space, Spin, Typography } from 'antd';
import { useState } from 'react';

import { downloadBpmn, getDfg } from '@/api/analytics';
import { ProcessGraph } from '@/components/ProcessGraph';
import { getErrorMessage, notifyError } from '@/lib/notify';

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

  const { data, isLoading } = useQuery({
    queryKey: ['dfg', projectId, vdId, minEdge],
    queryFn: () => getDfg(projectId, vdId, { min_edge_frequency_pct: minEdge }),
  });

  const bpmnMutation = useMutation({
    mutationFn: () => downloadBpmn(projectId, vdId, `${vdName}.bpmn`),
    onError: (error) => notifyError(getErrorMessage(error, 'Не удалось экспортировать BPMN')),
  });

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap size="large">
        <Space>
          <Typography.Text type="secondary">Порог частоты рёбер:</Typography.Text>
          <Slider
            min={0}
            max={50}
            value={minEdge}
            onChange={setMinEdge}
            style={{ width: 200 }}
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
