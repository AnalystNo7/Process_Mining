import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { addWidget, type WidgetCreatePayload } from '@/api/dashboards';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

import { BAR_SOURCES, HEATMAP_AXES, KPI_METRICS, WIDGET_TYPES } from './widgetMeta';

interface AddWidgetFormValues {
  widget_type: string;
  title: string;
  metric?: string;
  data_source?: string;
  y_axis?: string;
  dimension?: string;
  sla_target_hours?: number;
}

const WIDE_TYPES = new Set([
  'rework_table',
  'resource_analysis_table',
  'sla_compliance_table',
  'top_paths_graph',
  'process_graph',
  'operation_durations_boxplot',
  'case_duration_cdf',
  'duration_bottleneck_heatmap',
  'sojourn_vs_own',
]);

const HEATMAP_DIMENSIONS = [
  { value: 'department', label: 'Департамент' },
  { value: 'resource', label: 'Исполнитель' },
];

function buildConfig(values: AddWidgetFormValues): Record<string, unknown> {
  if (values.widget_type === 'kpi_card') {
    const metric = KPI_METRICS.find((m) => m.value === values.metric);
    return { metric: values.metric, format: metric?.format ?? 'number' };
  }
  if (values.widget_type === 'bar_chart' || values.widget_type === 'line_chart') {
    return { data_source: values.data_source };
  }
  if (values.widget_type === 'heatmap') {
    return { y_axis: values.y_axis };
  }
  if (values.widget_type === 'duration_bottleneck_heatmap') {
    return { dimension: values.dimension ?? 'department', activity_level: 'raw' };
  }
  if (values.widget_type === 'case_duration_cdf') {
    return { sla_target_hours: values.sla_target_hours ?? 24 };
  }
  return {};
}

export function AddWidgetModal({
  dashboardId,
  open,
  onClose,
  defaultTab,
}: {
  dashboardId: number;
  open: boolean;
  onClose: () => void;
  /** Ключ активной вкладки дашборда — новый виджет уйдёт в неё. */
  defaultTab?: string;
}) {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<AddWidgetFormValues>();
  const widgetType = Form.useWatch('widget_type', form);

  const addMutation = useMutation({
    mutationFn: (payload: WidgetCreatePayload) => addWidget(dashboardId, payload),
    onSuccess: () => {
      notifySuccess('Виджет добавлен');
      void queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] });
      form.resetFields();
      onClose();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const submit = (values: AddWidgetFormValues) => {
    addMutation.mutate({
      widget_type: values.widget_type,
      title: values.title,
      config: buildConfig(values),
      tab: defaultTab,
      grid_width: values.widget_type === 'kpi_card' ? 3 : WIDE_TYPES.has(values.widget_type) ? 12 : 6,
      grid_height: values.widget_type === 'kpi_card' ? 2 : 4,
    });
  };

  return (
    <Modal
      title="Добавить виджет"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={addMutation.isPending}
      okText="Добавить"
      cancelText="Отмена"
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={submit}>
        <Form.Item
          name="widget_type"
          label="Тип виджета"
          rules={[{ required: true, message: 'Выберите тип' }]}
        >
          <Select options={WIDGET_TYPES} placeholder="Тип виджета" />
        </Form.Item>
        <Form.Item
          name="title"
          label="Заголовок"
          rules={[{ required: true, message: 'Введите заголовок' }]}
        >
          <Input maxLength={255} />
        </Form.Item>
        {widgetType === 'kpi_card' && (
          <Form.Item
            name="metric"
            label="Метрика"
            rules={[{ required: true, message: 'Выберите метрику' }]}
          >
            <Select options={KPI_METRICS} />
          </Form.Item>
        )}
        {(widgetType === 'bar_chart' || widgetType === 'line_chart') && (
          <Form.Item
            name="data_source"
            label="Источник данных"
            rules={[{ required: true, message: 'Выберите источник' }]}
          >
            <Select options={BAR_SOURCES} />
          </Form.Item>
        )}
        {widgetType === 'heatmap' && (
          <Form.Item
            name="y_axis"
            label="Ось Y"
            rules={[{ required: true, message: 'Выберите ось' }]}
          >
            <Select options={HEATMAP_AXES} />
          </Form.Item>
        )}
        {widgetType === 'duration_bottleneck_heatmap' && (
          <Form.Item name="dimension" label="Разрез" initialValue="department">
            <Select options={HEATMAP_DIMENSIONS} />
          </Form.Item>
        )}
        {widgetType === 'case_duration_cdf' && (
          <Form.Item name="sla_target_hours" label="Цель SLA, часов" initialValue={24}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
