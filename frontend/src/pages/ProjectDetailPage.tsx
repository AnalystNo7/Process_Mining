import { ArrowLeftOutlined, UploadOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  List,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  deleteDataset,
  getDatasetHealth,
  listDatasets,
  type PhysicalDataset,
} from '@/api/physicalDatasets';
import { getProject } from '@/api/projects';
import {
  DATASET_STATUS_COLOR,
  DATASET_STATUS_LABEL,
  HEALTH_COLOR,
  HEALTH_LABEL,
  SEVERITY_COLOR,
} from '@/features/datasets/datasetStatus';
import { UploadWizard } from '@/features/datasets/UploadWizard';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

export function ProjectDetailPage() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const queryClient = useQueryClient();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [healthFor, setHealthFor] = useState<PhysicalDataset | null>(null);

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId),
  });

  const { data: datasets, isLoading } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => listDatasets(projectId),
    refetchInterval: (query) =>
      query.state.data?.items.some((d) => d.status === 'validating') ? 2000 : false,
  });

  const deleteMutation = useMutation({
    mutationFn: (datasetId: number) => deleteDataset(projectId, datasetId),
    onSuccess: () => {
      notifySuccess('Датасет удалён');
      void queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const columns: TableColumnsType<PhysicalDataset> = [
    {
      title: 'Название',
      key: 'name',
      render: (_, dataset) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{dataset.name}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {dataset.file_name}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={DATASET_STATUS_COLOR[status] ?? 'default'}>
          {DATASET_STATUS_LABEL[status] ?? status}
        </Tag>
      ),
    },
    {
      title: 'Объём',
      key: 'volume',
      render: (_, dataset) =>
        dataset.status === 'ready' ? (
          <Space size={4} wrap>
            <Tag>событий: {dataset.total_events}</Tag>
            <Tag>кейсов: {dataset.total_cases}</Tag>
            <Tag>операций: {dataset.unique_activities}</Tag>
          </Space>
        ) : (
          '—'
        ),
    },
    {
      title: 'Качество данных',
      key: 'health',
      render: (_, dataset) =>
        dataset.status === 'ready' ? (
          <Button type="link" size="small" onClick={() => setHealthFor(dataset)}>
            <Tag color={HEALTH_COLOR[dataset.health_status] ?? 'default'}>
              {HEALTH_LABEL[dataset.health_status] ?? dataset.health_status}
            </Tag>
          </Button>
        ) : (
          '—'
        ),
    },
    {
      title: 'Загружен',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 110,
      render: (_, dataset) => (
        <Popconfirm
          title="Удалить датасет?"
          description="Виртуальные датасеты на его основе сохранятся."
          okText="Удалить"
          cancelText="Отмена"
          onConfirm={() => deleteMutation.mutate(dataset.id)}
        >
          <Button size="small" danger>
            Удалить
          </Button>
        </Popconfirm>
      ),
    },
  ];

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

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          Физические датасеты
        </Typography.Title>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={() => setWizardOpen(true)}
        >
          Загрузить датасет
        </Button>
      </div>
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={datasets?.items ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
      />

      <UploadWizard
        projectId={projectId}
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
      />

      <Drawer
        title={`Качество данных: ${healthFor?.name ?? ''}`}
        open={healthFor != null}
        onClose={() => setHealthFor(null)}
        width={460}
      >
        {healthFor && (
          <HealthReportView projectId={projectId} datasetId={healthFor.id} />
        )}
      </Drawer>
    </div>
  );
}

function HealthReportView({
  projectId,
  datasetId,
}: {
  projectId: number;
  datasetId: number;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['dataset-health', projectId, datasetId],
    queryFn: () => getDatasetHealth(projectId, datasetId),
  });

  return (
    <List
      loading={isLoading}
      dataSource={data?.checks ?? []}
      locale={{ emptyText: 'Проверки не выполнялись' }}
      renderItem={(check) => (
        <List.Item>
          <List.Item.Meta
            title={
              <Space>
                <Tag color={SEVERITY_COLOR[check.severity] ?? 'default'}>
                  {check.severity}
                </Tag>
                {check.name}
              </Space>
            }
            description={check.message}
          />
        </List.Item>
      )}
    />
  );
}
