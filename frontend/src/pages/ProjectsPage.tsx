import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import {
  createProject,
  deleteProject,
  listProjects,
  updateProject,
  type Project,
  type ProjectPayload,
} from '@/api/projects';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';
import { useAuthStore } from '@/stores/authStore';

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [form] = Form.useForm<ProjectPayload>();
  const [editing, setEditing] = useState<Project | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => listProjects({ page_size: 200 }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['projects'] });
  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const saveMutation = useMutation({
    mutationFn: (values: ProjectPayload) =>
      editing ? updateProject(editing.id, values) : createProject(values),
    onSuccess: () => {
      notifySuccess(editing ? 'Проект обновлён' : 'Проект создан');
      invalidate();
      closeModal();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      notifySuccess('Проект удалён');
      invalidate();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };
  const openEdit = (project: Project) => {
    setEditing(project);
    form.setFieldsValue({ name: project.name, description: project.description });
    setModalOpen(true);
  };

  const canManage = (project: Project) =>
    currentUser?.role === 'admin' || project.created_by.id === currentUser?.id;

  const columns: TableColumnsType<Project> = [
    {
      title: 'Название',
      key: 'name',
      render: (_, project) => (
        <Link to={`/projects/${project.id}`}>{project.name}</Link>
      ),
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      render: (value: string | null) => value ?? '—',
    },
    {
      title: 'Владелец',
      key: 'owner',
      render: (_, project) => project.created_by.full_name ?? project.created_by.username,
    },
    {
      title: 'Датасеты',
      key: 'datasets',
      render: (_, project) => (
        <Space size={4}>
          <Tag>физ. {project.physical_datasets_count}</Tag>
          <Tag>вирт. {project.virtual_datasets_count}</Tag>
        </Space>
      ),
    },
    { title: 'Дашборды', dataIndex: 'dashboards_count', key: 'dashboards_count' },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 180,
      render: (_, project) =>
        canManage(project) ? (
          <Space>
            <Button size="small" onClick={() => openEdit(project)}>
              Изменить
            </Button>
            <Popconfirm
              title="Удалить проект?"
              description="Действие нельзя отменить."
              okText="Удалить"
              cancelText="Отмена"
              onConfirm={() => deleteMutation.mutate(project.id)}
            >
              <Button size="small" danger>
                Удалить
              </Button>
            </Popconfirm>
          </Space>
        ) : null,
    },
  ];

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Проекты</h1>
          <div className="page-sub">Список проектов, к которым у вас есть доступ.</div>
        </div>
        <div className="page-head-actions">
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Новый проект
          </Button>
        </div>
      </div>
      <div className="card">
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={data?.items ?? []}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
        />
      </div>
      <Modal
        title={editing ? 'Изменить проект' : 'Новый проект'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={() => form.submit()}
        confirmLoading={saveMutation.isPending}
        okText="Сохранить"
        cancelText="Отмена"
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => saveMutation.mutate(values)}
        >
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
