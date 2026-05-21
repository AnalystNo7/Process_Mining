import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';

import {
  createGlobalRole,
  deleteGlobalRole,
  listGlobalRoles,
  updateGlobalRole,
  type GlobalRolePayload,
  type GlobalRoleTemplate,
} from '@/api/globalRoles';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

export function GlobalRolesPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<GlobalRolePayload>();
  const [editing, setEditing] = useState<GlobalRoleTemplate | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['global-roles'],
    queryFn: listGlobalRoles,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['global-roles'] });
  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const saveMutation = useMutation({
    mutationFn: (values: GlobalRolePayload) =>
      editing ? updateGlobalRole(editing.id, values) : createGlobalRole(values),
    onSuccess: () => {
      notifySuccess(editing ? 'Шаблон обновлён' : 'Шаблон создан');
      invalidate();
      closeModal();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteGlobalRole,
    onSuccess: () => {
      notifySuccess('Шаблон удалён');
      invalidate();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ patterns: [], sort_order: 100, is_active: true });
    setModalOpen(true);
  };
  const openEdit = (template: GlobalRoleTemplate) => {
    setEditing(template);
    form.setFieldsValue({
      role_name: template.role_name,
      patterns: template.patterns,
      sort_order: template.sort_order,
      is_active: template.is_active,
    });
    setModalOpen(true);
  };

  const columns: TableColumnsType<GlobalRoleTemplate> = [
    { title: 'Роль', dataIndex: 'role_name', key: 'role_name' },
    {
      title: 'Паттерны авторазметки',
      dataIndex: 'patterns',
      key: 'patterns',
      render: (patterns: string[]) =>
        patterns.length > 0 ? (
          <Space size={4} wrap>
            {patterns.map((pattern) => (
              <Tag key={pattern}>{pattern}</Tag>
            ))}
          </Space>
        ) : (
          '—'
        ),
    },
    {
      title: 'Порядок',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 100,
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 120,
      render: (active: boolean) =>
        active ? <Tag color="green">Активна</Tag> : <Tag>Отключена</Tag>,
    },
    {
      title: '',
      key: 'actions',
      width: 180,
      render: (_, template) => (
        <Space>
          <Button size="small" onClick={() => openEdit(template)}>
            Изменить
          </Button>
          <Popconfirm
            title="Удалить шаблон роли?"
            okText="Удалить"
            cancelText="Отмена"
            onConfirm={() => deleteMutation.mutate(template.id)}
          >
            <Button size="small" danger>
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          Глобальные шаблоны ролей
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Новая роль
        </Button>
      </div>
      <Typography.Paragraph type="secondary">
        Применяются как стартовая точка при создании новых проектов. Существующие
        проекты не меняются.
      </Typography.Paragraph>
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data?.items ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
      />
      <Modal
        title={editing ? 'Изменить роль' : 'Новая роль'}
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
            name="role_name"
            label="Название роли"
            rules={[{ required: true, message: 'Введите название роли' }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item
            name="patterns"
            label="Паттерны авторазметки"
            extra="Подстроки названий подразделений. Enter — добавить."
          >
            <Select mode="tags" tokenSeparators={[',']} open={false} />
          </Form.Item>
          <Form.Item name="sort_order" label="Порядок сортировки">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
