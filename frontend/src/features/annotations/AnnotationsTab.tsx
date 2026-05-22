import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  DatePicker,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useState } from 'react';

import {
  createAnnotation,
  deleteAnnotation,
  listAnnotations,
  updateAnnotation,
  type Annotation,
  type AnnotationTargetType,
} from '@/api/annotations';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';
import { useAuthStore } from '@/stores/authStore';

const TARGET_TYPES: { value: AnnotationTargetType; label: string }[] = [
  { value: 'node', label: 'Узел графа' },
  { value: 'edge', label: 'Переход (ребро)' },
  { value: 'case', label: 'Кейс' },
  { value: 'time_range', label: 'Период' },
];

const TARGET_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  TARGET_TYPES.map((t) => [t.value, t.label])
);

interface AnnotationFormValues {
  target_type: AnnotationTargetType;
  text: string;
  activity?: string;
  from?: string;
  to?: string;
  case_id?: string;
  dates?: [Dayjs, Dayjs];
  context?: string;
}

function formatTarget(annotation: Annotation): string {
  const t = annotation.target;
  switch (annotation.target_type) {
    case 'node':
      return String(t.activity ?? '');
    case 'edge':
      return `${String(t.from ?? '')} → ${String(t.to ?? '')}`;
    case 'case':
      return String(t.case_id ?? '');
    case 'time_range':
      return `${String(t.start_date ?? '')} — ${String(t.end_date ?? '')}`;
    default:
      return '';
  }
}

export function AnnotationsTab({ vdId }: { vdId: number }) {
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [form] = Form.useForm<AnnotationFormValues>();
  const [editing, setEditing] = useState<Annotation | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const targetType = Form.useWatch('target_type', form);

  const { data, isLoading } = useQuery({
    queryKey: ['annotations', vdId],
    queryFn: () => listAnnotations(vdId),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['annotations', vdId] });
  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const saveMutation = useMutation({
    mutationFn: (values: AnnotationFormValues) => {
      if (editing) {
        return updateAnnotation(editing.id, values.text);
      }
      const target: Record<string, unknown> = {};
      if (values.target_type === 'node') {
        target.activity = values.activity;
      } else if (values.target_type === 'edge') {
        target.from = values.from;
        target.to = values.to;
      } else if (values.target_type === 'case') {
        target.case_id = values.case_id;
      } else {
        target.start_date = values.dates?.[0].format('YYYY-MM-DD');
        target.end_date = values.dates?.[1].format('YYYY-MM-DD');
        if (values.context) {
          target.context = values.context;
        }
      }
      return createAnnotation(vdId, {
        target_type: values.target_type,
        target,
        text: values.text,
      });
    },
    onSuccess: () => {
      notifySuccess(editing ? 'Аннотация обновлена' : 'Аннотация создана');
      invalidate();
      closeModal();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAnnotation,
    onSuccess: () => {
      notifySuccess('Аннотация удалена');
      invalidate();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ target_type: 'node' });
    setModalOpen(true);
  };
  const openEdit = (annotation: Annotation) => {
    setEditing(annotation);
    form.resetFields();
    form.setFieldsValue({ target_type: annotation.target_type, text: annotation.text });
    setModalOpen(true);
  };

  const canManage = (annotation: Annotation) =>
    currentUser?.role === 'admin' || annotation.author_id === currentUser?.id;

  const columns: TableColumnsType<Annotation> = [
    {
      title: 'Тип',
      dataIndex: 'target_type',
      key: 'target_type',
      width: 150,
      render: (value: string) => <Tag>{TARGET_TYPE_LABEL[value] ?? value}</Tag>,
    },
    {
      title: 'Объект',
      key: 'target',
      render: (_, annotation) => formatTarget(annotation),
    },
    { title: 'Пометка', dataIndex: 'text', key: 'text' },
    { title: 'Автор', dataIndex: 'author_name', key: 'author_name', width: 160 },
    {
      title: 'Создана',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 170,
      render: (_, annotation) =>
        canManage(annotation) ? (
          <Space>
            <Button size="small" onClick={() => openEdit(annotation)}>
              Изменить
            </Button>
            <Popconfirm
              title="Удалить аннотацию?"
              okText="Удалить"
              cancelText="Отмена"
              onConfirm={() => deleteMutation.mutate(annotation.id)}
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
      <Typography.Paragraph type="secondary">
        Текстовые пометки на узлах графа, переходах, кейсах и периодах. Видны всем
        аналитикам проекта.
      </Typography.Paragraph>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Новая аннотация
        </Button>
      </div>
      <Table
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data?.items ?? []}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
      />

      <Modal
        title={editing ? 'Изменить аннотацию' : 'Новая аннотация'}
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
            name="target_type"
            label="Тип объекта"
            rules={[{ required: true }]}
          >
            <Select options={TARGET_TYPES} disabled={editing != null} />
          </Form.Item>

          {!editing && targetType === 'node' && (
            <Form.Item
              name="activity"
              label="Операция"
              rules={[{ required: true, message: 'Укажите операцию' }]}
            >
              <Input />
            </Form.Item>
          )}
          {!editing && targetType === 'edge' && (
            <>
              <Form.Item
                name="from"
                label="Операция-источник"
                rules={[{ required: true, message: 'Укажите операцию' }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                name="to"
                label="Операция-приёмник"
                rules={[{ required: true, message: 'Укажите операцию' }]}
              >
                <Input />
              </Form.Item>
            </>
          )}
          {!editing && targetType === 'case' && (
            <Form.Item
              name="case_id"
              label="ID кейса"
              rules={[{ required: true, message: 'Укажите ID кейса' }]}
            >
              <Input />
            </Form.Item>
          )}
          {!editing && targetType === 'time_range' && (
            <>
              <Form.Item
                name="dates"
                label="Период"
                rules={[{ required: true, message: 'Укажите период' }]}
              >
                <DatePicker.RangePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="context" label="Контекст (необязательно)">
                <Input placeholder="например, operation:Согласование" />
              </Form.Item>
            </>
          )}

          <Form.Item
            name="text"
            label="Текст пометки"
            rules={[{ required: true, message: 'Введите текст' }]}
          >
            <Input.TextArea rows={3} maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
