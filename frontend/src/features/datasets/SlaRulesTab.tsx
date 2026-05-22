import { PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useState } from 'react';

import {
  createSlaRule,
  deleteSlaRule,
  listSlaRules,
  updateSlaRule,
  type SlaRule,
  type SlaUnit,
} from '@/api/slaRules';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

const SLA_UNITS: { value: SlaUnit; label: string }[] = [
  { value: 'workdays', label: 'Рабочие дни' },
  { value: 'calendar_days', label: 'Календарные дни' },
  { value: 'workhours', label: 'Рабочие часы' },
  { value: 'hours', label: 'Часы' },
];

const UNIT_LABEL: Record<string, string> = Object.fromEntries(
  SLA_UNITS.map((u) => [u.value, u.label])
);

interface SlaFormValues {
  role: string;
  operation_pattern: string;
  sla_value: number;
  sla_unit: SlaUnit;
  tolerance_hours: number;
  target_compliance_pct: number;
  effective_from: Dayjs;
  description?: string;
}

export function SlaRulesTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<SlaFormValues>();
  const [editing, setEditing] = useState<SlaRule | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['sla-rules', projectId],
    queryFn: () => listSlaRules(projectId),
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['sla-rules', projectId] });
  const closeModal = () => {
    setModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const saveMutation = useMutation({
    mutationFn: (values: SlaFormValues) => {
      const payload = {
        role: values.role,
        operation_pattern: values.operation_pattern,
        sla_value: values.sla_value,
        sla_unit: values.sla_unit,
        tolerance_hours: values.tolerance_hours,
        target_compliance_pct: values.target_compliance_pct,
        effective_from: values.effective_from.format('YYYY-MM-DD'),
        description: values.description ?? null,
      };
      return editing
        ? updateSlaRule(editing.id, payload)
        : createSlaRule(projectId, payload);
    },
    onSuccess: () => {
      notifySuccess(editing ? 'Правило обновлено' : 'Правило создано');
      invalidate();
      closeModal();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSlaRule,
    onSuccess: () => {
      notifySuccess('Правило удалено');
      invalidate();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      operation_pattern: '*',
      sla_unit: 'workdays',
      tolerance_hours: 0,
      target_compliance_pct: 90,
      effective_from: dayjs(),
    });
    setModalOpen(true);
  };
  const openEdit = (rule: SlaRule) => {
    setEditing(rule);
    form.setFieldsValue({
      role: rule.role,
      operation_pattern: rule.operation_pattern,
      sla_value: rule.sla_value,
      sla_unit: rule.sla_unit,
      tolerance_hours: rule.tolerance_hours,
      target_compliance_pct: rule.target_compliance_pct,
      effective_from: dayjs(rule.effective_from),
      description: rule.description ?? undefined,
    });
    setModalOpen(true);
  };

  const columns: TableColumnsType<SlaRule> = [
    { title: 'Роль', dataIndex: 'role', key: 'role' },
    { title: 'Операция', dataIndex: 'operation_pattern', key: 'operation_pattern' },
    {
      title: 'Норматив',
      key: 'sla',
      render: (_, rule) => `${rule.sla_value} ${UNIT_LABEL[rule.sla_unit] ?? rule.sla_unit}`,
    },
    {
      title: 'Допуск, ч',
      dataIndex: 'tolerance_hours',
      key: 'tolerance_hours',
      width: 110,
    },
    {
      title: 'Цель, %',
      dataIndex: 'target_compliance_pct',
      key: 'target_compliance_pct',
      width: 100,
    },
    {
      title: 'Действует с',
      dataIndex: 'effective_from',
      key: 'effective_from',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: '',
      key: 'actions',
      width: 180,
      render: (_, rule) => (
        <Space>
          <Button size="small" onClick={() => openEdit(rule)}>
            Изменить
          </Button>
          <Popconfirm
            title="Удалить правило?"
            okText="Удалить"
            cancelText="Отмена"
            onConfirm={() => deleteMutation.mutate(rule.id)}
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
      <Typography.Paragraph type="secondary">
        SLA-правила задают нормативы длительности операций. Виртуальные датасеты
        снимают действующие правила в момент создания.
      </Typography.Paragraph>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Новое правило
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
        title={editing ? 'Изменить SLA-правило' : 'Новое SLA-правило'}
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
            name="role"
            label="Роль"
            extra="* — правило применяется к любой роли"
            rules={[{ required: true, message: 'Введите роль' }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item
            name="operation_pattern"
            label="Операция"
            extra="* — правило применяется к любой операции"
            rules={[{ required: true, message: 'Введите операцию' }]}
          >
            <Input maxLength={500} />
          </Form.Item>
          <Space size="middle" style={{ display: 'flex' }}>
            <Form.Item
              name="sla_value"
              label="Норматив"
              rules={[{ required: true, message: 'Укажите значение' }]}
            >
              <InputNumber min={0.01} step={0.5} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="sla_unit"
              label="Единица"
              rules={[{ required: true }]}
            >
              <Select options={SLA_UNITS} style={{ width: 180 }} />
            </Form.Item>
          </Space>
          <Space size="middle" style={{ display: 'flex' }}>
            <Form.Item name="tolerance_hours" label="Допуск, ч" rules={[{ required: true }]}>
              <InputNumber min={0} step={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="target_compliance_pct"
              label="Целевое соответствие, %"
              rules={[{ required: true }]}
            >
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item
            name="effective_from"
            label="Действует с"
            rules={[{ required: true, message: 'Укажите дату' }]}
          >
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
