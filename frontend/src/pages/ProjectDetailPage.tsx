import { ArrowLeftOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Descriptions, Tabs, Typography } from 'antd';
import { Link, useParams } from 'react-router-dom';

import { getProject } from '@/api/projects';
import { PhysicalDatasetsTab } from '@/features/datasets/PhysicalDatasetsTab';
import { RoleMappingTab } from '@/features/datasets/RoleMappingTab';
import { SlaRulesTab } from '@/features/datasets/SlaRulesTab';
import { VirtualDatasetsTab } from '@/features/datasets/VirtualDatasetsTab';

export function ProjectDetailPage() {
  const params = useParams();
  const projectId = Number(params.projectId);

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId),
  });

  return (
    <div>
      <Link to="/projects">
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          К списку проектов
        </Button>
      </Link>
      <Typography.Title level={3} style={{ marginTop: 8 }}>
        {project?.name ?? 'Проект'}
      </Typography.Title>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="Описание">
            {project?.description ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Владелец">
            {project?.created_by.full_name ?? project?.created_by.username ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Виртуальных датасетов">
            {project?.virtual_datasets_count ?? 0}
          </Descriptions.Item>
          <Descriptions.Item label="Дашбордов">
            {project?.dashboards_count ?? 0}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs
        defaultActiveKey="physical"
        items={[
          {
            key: 'physical',
            label: 'Физические датасеты',
            children: <PhysicalDatasetsTab projectId={projectId} />,
          },
          {
            key: 'roles',
            label: 'Разметка ролей',
            children: <RoleMappingTab projectId={projectId} />,
          },
          {
            key: 'virtual',
            label: 'Виртуальные датасеты',
            children: <VirtualDatasetsTab projectId={projectId} />,
          },
          {
            key: 'sla',
            label: 'SLA-правила',
            children: <SlaRulesTab projectId={projectId} />,
          },
        ]}
      />
    </div>
  );
}
