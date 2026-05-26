import { ArrowLeftOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getVirtualDataset } from '@/api/virtualDatasets';
import { AnnotationsTab } from '@/features/annotations/AnnotationsTab';
import { CasesTab } from '@/features/analytics/CasesTab';
import { ProcessGraphTab } from '@/features/analytics/ProcessGraphTab';
import { DashboardsTab } from '@/features/dashboards/DashboardsTab';

type TabKey = 'dashboards' | 'graph' | 'cases' | 'annotations';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'dashboards', label: 'Дашборды' },
  { key: 'graph', label: 'Процесс' },
  { key: 'cases', label: 'Кейсы' },
  { key: 'annotations', label: 'Аннотации' },
];

export function VirtualDatasetPage() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const vdId = Number(params.vdId);
  const [active, setActive] = useState<TabKey>('dashboards');

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
      <div className="page-head">
        <div>
          <h1>{vdName}</h1>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Разделы датасета">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={active === tab.key}
            onClick={() => setActive(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {active === 'dashboards' && <DashboardsTab projectId={projectId} vdId={vdId} />}
        {active === 'graph' && (
          <ProcessGraphTab projectId={projectId} vdId={vdId} vdName={vdName} />
        )}
        {active === 'cases' && <CasesTab projectId={projectId} vdId={vdId} />}
        {active === 'annotations' && <AnnotationsTab vdId={vdId} />}
      </div>
    </div>
  );
}
