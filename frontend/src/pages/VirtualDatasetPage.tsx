import { ArrowLeftOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Button, Tabs, Typography } from 'antd';
import { Link, useParams } from 'react-router-dom';

import { getVirtualDataset } from '@/api/virtualDatasets';
import { CasesTab } from '@/features/analytics/CasesTab';
import { ProcessGraphTab } from '@/features/analytics/ProcessGraphTab';
import { VariantsTab } from '@/features/analytics/VariantsTab';
import { DashboardsTab } from '@/features/dashboards/DashboardsTab';

export function VirtualDatasetPage() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const vdId = Number(params.vdId);

  const { data: vd } = useQuery({
    queryKey: ['vd', vdId],
    queryFn: () => getVirtualDataset(projectId, vdId),
  });

  const vdName = vd?.name ?? 'Виртуальный датасет';

  return (
    <div>
      <Link to={`/projects/${projectId}`}>
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          К проекту
        </Button>
      </Link>
      <Typography.Title level={3} style={{ margin: '8px 0 16px' }}>
        {vdName}
      </Typography.Title>

      <Tabs
        defaultActiveKey="dashboards"
        items={[
          {
            key: 'dashboards',
            label: 'Дашборды',
            children: <DashboardsTab projectId={projectId} vdId={vdId} />,
          },
          {
            key: 'graph',
            label: 'Граф процесса',
            children: (
              <ProcessGraphTab projectId={projectId} vdId={vdId} vdName={vdName} />
            ),
          },
          {
            key: 'variants',
            label: 'Маршруты',
            children: <VariantsTab projectId={projectId} vdId={vdId} />,
          },
          {
            key: 'cases',
            label: 'Кейсы',
            children: <CasesTab projectId={projectId} vdId={vdId} />,
          },
        ]}
      />
    </div>
  );
}
