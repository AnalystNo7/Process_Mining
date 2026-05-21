import { ArrowLeftOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  createDashboard,
  deleteDashboard,
  listDashboards,
  type DashboardBrief,
} from '@/api/dashboards';
import { getVirtualDataset } from '@/api/virtualDatasets';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

interface DashboardFormValues {
  name: string;
  description?: string;
}

export function VirtualDatasetPage() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const vdId = Number(params.vdId);
  const queryClient = useQueryClient();
  const [form] = Form.useForm<DashboardFormValues>();
  const [modalOpen, setModalOpen] = useState(false);

  const { data: vd } = useQuery({
    queryKey: ['vd', vdId],
    queryFn: () => getVirtualDataset(projectId, vdId),
  });

  const { data: dashboards, isLoading } = useQuery({
    queryKey: ['dashboards', vdId],
    queryFn: () => listDashboards(projectId, vdId),
  });

  const createMutation = useMutation({
    mutationFn: (values: DashboardFormValues) =>
      createDashboard(projectId, vdId, values),
    onSuccess: () => {
      notifySuccess('Дашборд создан');
      void queryClient.invalidateQueries({ queryKey: ['dashboards', vdId] });
      setModalOpen(false);
      form.resetFields();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDashboard,
    onSuccess: () => {
      notifySuccess('Дашборд удалён');
      void queryClient.invalidateQueries({ queryKey: ['dashboards', vdId] });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const columns: TableColumnsType<DashboardBrief> = [
    {
      title: 'Название',
      key: 'name',
      render: (_, dashboard) => (
        <Link
          to={`/projects/${projectId}/virtual-datasets/${vdId}/dashboards/${dashboard.id}`}
        >
          {dashboard.name}
        </Link>
      ),
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 110,
      render: (_, dashboard) => (
        <Popconfirm
          title="Удалить дашборд?"
          okText="Удалить"
          cancelText="Отмена"
          onConfirm={() => deleteMutation.mutate(dashboard.id)}
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
      <Link to={`/projects/${projectId}`}>
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          К проекту
        </Button>
      </Link>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          margin: '8px 0 16px',
        }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          {vd?.name ?? 'Виртуальный датасет'}
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            setModalOpen(true);
          }}
        >
          Новый дашборд
        </Button>
      </div>
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={dashboards?.items ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
      />

      <Modal
        title="Новый дашборд"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
        okText="Создать"
        cancelText="Отмена"
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => createMutation.mutate(values)}
        >
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
