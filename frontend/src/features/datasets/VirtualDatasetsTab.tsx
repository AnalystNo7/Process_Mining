import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { listDatasets } from '@/api/physicalDatasets';
import {
  createVirtualDataset,
  deleteVirtualDataset,
  listVirtualDatasets,
  type CreateVirtualDatasetPayload,
  type VirtualDatasetBrief,
} from '@/api/virtualDatasets';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

export function VirtualDatasetsTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<CreateVirtualDatasetPayload>();
  const [modalOpen, setModalOpen] = useState(false);

  const { data: vds, isLoading } = useQuery({
    queryKey: ['virtual-datasets', projectId],
    queryFn: () => listVirtualDatasets(projectId),
  });

  const { data: physical } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => listDatasets(projectId),
  });

  const readyDatasets = physical?.items.filter((d) => d.status === 'ready') ?? [];
  const datasetName = (id: number) =>
    physical?.items.find((d) => d.id === id)?.name ?? `#${id}`;

  const createMutation = useMutation({
    mutationFn: (values: CreateVirtualDatasetPayload) =>
      createVirtualDataset(projectId, values),
    onSuccess: () => {
      notifySuccess('Виртуальный датасет создан');
      void queryClient.invalidateQueries({ queryKey: ['virtual-datasets', projectId] });
      setModalOpen(false);
      form.resetFields();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (vdId: number) => deleteVirtualDataset(projectId, vdId),
    onSuccess: () => {
      notifySuccess('Виртуальный датасет удалён');
      void queryClient.invalidateQueries({ queryKey: ['virtual-datasets', projectId] });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const columns: TableColumnsType<VirtualDatasetBrief> = [
    {
      title: 'Название',
      key: 'name',
      render: (_, vd) => (
        <Link to={`/projects/${projectId}/virtual-datasets/${vd.id}`}>{vd.name}</Link>
      ),
    },
    {
      title: 'Физический датасет',
      key: 'physical',
      render: (_, vd) => datasetName(vd.physical_dataset_id),
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
      render: (_, vd) => (
        <Popconfirm
          title="Удалить виртуальный датасет?"
          description="Дашборды на его основе также будут удалены."
          okText="Удалить"
          cancelText="Отмена"
          onConfirm={() => deleteMutation.mutate(vd.id)}
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
      <Typography.Paragraph type="secondary">
        Виртуальный датасет — неизменяемый снимок разметки ролей и SLA-правил
        поверх физического датасета. Аналитика и дашборды строятся на нём.
      </Typography.Paragraph>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          disabled={readyDatasets.length === 0}
          onClick={() => {
            form.resetFields();
            setModalOpen(true);
          }}
        >
          Создать виртуальный датасет
        </Button>
      </div>
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={vds?.items ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
      />

      <Modal
        title="Новый виртуальный датасет"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
        okText="Создать"
        cancelText="Отмена"
        destroyOnClose
      >
        {readyDatasets.length === 0 ? (
          <Alert
            type="info"
            message="Нет готовых физических датасетов. Сначала загрузите и обработайте файл."
          />
        ) : (
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
            <Form.Item
              name="physical_dataset_id"
              label="Физический датасет"
              rules={[{ required: true, message: 'Выберите датасет' }]}
            >
              <Select
                placeholder="Выберите физический датасет"
                options={readyDatasets.map((d) => ({ value: d.id, label: d.name }))}
              />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
}
