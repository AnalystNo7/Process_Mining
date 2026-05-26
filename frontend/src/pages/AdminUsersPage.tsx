import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  type TableColumnsType,
} from 'antd';
import { useState } from 'react';

import {
  createUser,
  deleteUser,
  listUsers,
  updateUser,
  type AppUser,
} from '@/api/users';
import type { UserRole } from '@/api/types';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';
import { useAuthStore } from '@/stores/authStore';

interface UserFormValues {
  username: string;
  full_name?: string;
  email?: string;
  role: UserRole;
  is_ldap: boolean;
  is_active: boolean;
  password?: string;
}

const ROLE_OPTIONS = [
  { value: 'analyst', label: 'Аналитик' },
  { value: 'admin', label: 'Администратор' },
];

export function AdminUsersPage() {
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [form] = Form.useForm<UserFormValues>();
  const [editing, setEditing] = useState<AppUser | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const isLdap = Form.useWatch('is_ldap', form);

  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers({ page_size: 200 }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['users'] });
  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const saveMutation = useMutation({
    mutationFn: (values: UserFormValues) => {
      const password = values.password ? values.password : undefined;
      if (editing) {
        return updateUser(editing.id, {
          full_name: values.full_name ?? null,
          email: values.email ?? null,
          role: values.role,
          is_active: values.is_active,
          password,
        });
      }
      return createUser({
        username: values.username,
        full_name: values.full_name ?? null,
        email: values.email ?? null,
        role: values.role,
        is_ldap: values.is_ldap,
        password,
      });
    },
    onSuccess: () => {
      notifySuccess(editing ? 'Пользователь обновлён' : 'Пользователь создан');
      invalidate();
      closeModal();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      notifySuccess('Пользователь удалён');
      invalidate();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ role: 'analyst', is_ldap: false, is_active: true });
    setModalOpen(true);
  };
  const openEdit = (user: AppUser) => {
    setEditing(user);
    form.setFieldsValue({
      username: user.username,
      full_name: user.full_name ?? undefined,
      email: user.email ?? undefined,
      role: user.role,
      is_ldap: user.is_ldap,
      is_active: user.is_active,
      password: undefined,
    });
    setModalOpen(true);
  };

  const columns: TableColumnsType<AppUser> = [
    { title: 'Логин', dataIndex: 'username', key: 'username' },
    {
      title: 'ФИО',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (value: string | null) => value ?? '—',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (value: string | null) => value ?? '—',
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      key: 'role',
      render: (role: UserRole) => (
        <Tag color={role === 'admin' ? 'gold' : 'blue'}>
          {role === 'admin' ? 'Администратор' : 'Аналитик'}
        </Tag>
      ),
    },
    {
      title: 'Тип входа',
      dataIndex: 'is_ldap',
      key: 'is_ldap',
      render: (ldap: boolean) => (ldap ? 'LDAP/AD' : 'Локальный'),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) =>
        active ? <Tag color="green">Активен</Tag> : <Tag color="red">Заблокирован</Tag>,
    },
    {
      title: 'Последний вход',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 180,
      render: (_, user) => (
        <Space>
          <Button size="small" onClick={() => openEdit(user)}>
            Изменить
          </Button>
          {user.id !== currentUser?.id && (
            <Popconfirm
              title="Удалить пользователя?"
              okText="Удалить"
              cancelText="Отмена"
              onConfirm={() => deleteMutation.mutate(user.id)}
            >
              <Button size="small" danger>
                Удалить
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Пользователи</h1>
          <div className="page-sub">Учётные записи и их роли.</div>
        </div>
        <div className="page-head-actions">
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Новый пользователь
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
        title={editing ? 'Изменить пользователя' : 'Новый пользователь'}
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
          {!editing && (
            <Form.Item
              name="username"
              label="Логин"
              rules={[
                { required: true, message: 'Введите логин' },
                {
                  pattern: /^[a-zA-Z0-9_.-]+$/,
                  message: 'Только латиница, цифры и символы _.-',
                },
              ]}
            >
              <Input autoComplete="off" />
            </Form.Item>
          )}
          <Form.Item name="full_name" label="ФИО">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
          {!editing && (
            <Form.Item name="is_ldap" valuePropName="checked">
              <Checkbox>Учётная запись LDAP/AD</Checkbox>
            </Form.Item>
          )}
          {editing && (
            <Form.Item name="is_active" label="Активен" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
          {!isLdap && (
            <Form.Item
              name="password"
              label={editing ? 'Новый пароль' : 'Пароль'}
              rules={[
                { required: !editing, message: 'Введите пароль' },
                { min: 8, message: 'Минимум 8 символов' },
              ]}
              extra={editing ? 'Оставьте пустым, чтобы не менять.' : undefined}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
