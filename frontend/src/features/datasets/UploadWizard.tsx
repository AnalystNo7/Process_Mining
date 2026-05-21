import { InboxOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Result,
  Select,
  Space,
  Spin,
  Steps,
  Table,
  Typography,
  Upload,
} from 'antd';
import { useEffect, useState } from 'react';

import {
  createDataset,
  getDataset,
  previewDataset,
  type PreviewResponse,
} from '@/api/physicalDatasets';
import { getErrorMessage, notifyError } from '@/lib/notify';

import { isTerminalStatus } from './datasetStatus';

const LOGICAL_FIELDS: { key: string; label: string; required: boolean }[] = [
  { key: 'case_id', label: 'ID кейса (документа)', required: true },
  { key: 'activity', label: 'Операция', required: true },
  { key: 'timestamp_start', label: 'Начало операции', required: true },
  { key: 'timestamp_end', label: 'Конец операции', required: true },
  { key: 'resource', label: 'Исполнитель', required: false },
  { key: 'department', label: 'Подразделение', required: false },
];

interface MappingFormValues {
  name: string;
  save_as_template: boolean;
  mapping: Record<string, string | undefined>;
}

interface UploadWizardProps {
  projectId: number;
  open: boolean;
  onClose: () => void;
}

export function UploadWizard({ projectId, open, onClose }: UploadWizardProps) {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<MappingFormValues>();
  const [step, setStep] = useState(0);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [datasetId, setDatasetId] = useState<number | null>(null);

  const handleClose = () => {
    setStep(0);
    setPreview(null);
    setDatasetId(null);
    form.resetFields();
    onClose();
  };

  const previewMutation = useMutation({
    mutationFn: (file: File) => previewDataset(projectId, file),
    onSuccess: (data, file) => {
      setPreview(data);
      form.setFieldsValue({
        name: file.name.replace(/\.xlsx$/i, ''),
        save_as_template: false,
        mapping: data.suggested_mapping,
      });
      setStep(1);
    },
    onError: (error) => notifyError(getErrorMessage(error, 'Не удалось прочитать файл')),
  });

  const createMutation = useMutation({
    mutationFn: (values: MappingFormValues) => {
      const mapping: Record<string, string> = {};
      for (const [field, column] of Object.entries(values.mapping)) {
        if (column) {
          mapping[field] = column;
        }
      }
      return createDataset(projectId, {
        name: values.name,
        preview_token: preview?.preview_token ?? '',
        column_mapping: mapping,
        save_as_template: values.save_as_template,
      });
    },
    onSuccess: (data) => {
      setDatasetId(data.id);
      setStep(2);
    },
    onError: (error) =>
      notifyError(getErrorMessage(error, 'Не удалось запустить загрузку')),
  });

  const { data: dataset } = useQuery({
    queryKey: ['dataset-progress', projectId, datasetId],
    queryFn: () => getDataset(projectId, datasetId as number),
    enabled: datasetId != null && step === 2,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && isTerminalStatus(status) ? false : 1500;
    },
  });

  useEffect(() => {
    if (dataset && isTerminalStatus(dataset.status)) {
      void queryClient.invalidateQueries({ queryKey: ['datasets', projectId] });
    }
  }, [dataset, projectId, queryClient]);

  const columnOptions =
    preview?.columns.map((column) => ({ value: column.name, label: column.name })) ?? [];

  const renderFooter = () => {
    if (step === 0) {
      return [
        <Button key="cancel" onClick={handleClose}>
          Отмена
        </Button>,
      ];
    }
    if (step === 1) {
      return [
        <Button key="back" onClick={() => setStep(0)}>
          Назад
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={createMutation.isPending}
          onClick={() => form.submit()}
        >
          Загрузить
        </Button>,
      ];
    }
    const done = dataset != null && isTerminalStatus(dataset.status);
    return [
      <Button key="close" type="primary" disabled={!done} onClick={handleClose}>
        Закрыть
      </Button>,
    ];
  };

  return (
    <Modal
      title="Загрузка датасета"
      open={open}
      onCancel={handleClose}
      footer={renderFooter()}
      width={780}
      destroyOnClose
    >
      <Steps
        size="small"
        current={step}
        style={{ marginBottom: 24 }}
        items={[{ title: 'Файл' }, { title: 'Сопоставление' }, { title: 'Обработка' }]}
      />

      {step === 0 && (
        <Spin spinning={previewMutation.isPending} tip="Чтение файла…">
          <Upload.Dragger
            accept=".xlsx"
            maxCount={1}
            showUploadList={false}
            beforeUpload={(file) => {
              previewMutation.mutate(file);
              return false;
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">
              Перетащите сюда .xlsx-файл журнала событий
            </p>
            <p className="ant-upload-hint">Поддерживается только формат Excel (.xlsx)</p>
          </Upload.Dragger>
        </Spin>
      )}

      {step === 1 && preview && (
        <div>
          <Typography.Paragraph type="secondary">
            Найдено колонок: {preview.columns.length}, строк: {preview.total_rows}.
            Проверьте предпросмотр и сопоставьте колонки файла стандартным полям.
          </Typography.Paragraph>
          <Table
            size="small"
            scroll={{ x: true }}
            pagination={false}
            style={{ marginBottom: 16 }}
            rowKey="__row"
            dataSource={preview.preview_rows.map((row, index) => ({
              ...row,
              __row: index,
            }))}
            columns={preview.columns.map((column) => ({
              title: column.name,
              dataIndex: column.name,
              key: column.name,
              ellipsis: true,
              render: (value: unknown) => (value == null ? '—' : String(value)),
            }))}
          />
          <Form form={form} layout="vertical" onFinish={createMutation.mutate}>
            <Form.Item
              name="name"
              label="Название датасета"
              rules={[{ required: true, message: 'Введите название' }]}
            >
              <Input maxLength={255} />
            </Form.Item>
            {LOGICAL_FIELDS.map((field) => (
              <Form.Item
                key={field.key}
                name={['mapping', field.key]}
                label={field.label + (field.required ? '' : ' (необязательно)')}
                rules={
                  field.required
                    ? [{ required: true, message: 'Выберите колонку' }]
                    : undefined
                }
              >
                <Select
                  allowClear={!field.required}
                  placeholder="Колонка файла"
                  options={columnOptions}
                />
              </Form.Item>
            ))}
            <Form.Item name="save_as_template" valuePropName="checked">
              <Checkbox>Сохранить сопоставление как шаблон проекта</Checkbox>
            </Form.Item>
          </Form>
        </div>
      )}

      {step === 2 && (
        <div>
          {!dataset || !isTerminalStatus(dataset.status) ? (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <Spin tip="Идёт обработка файла…" size="large">
                <div style={{ height: 48 }} />
              </Spin>
            </div>
          ) : dataset.status === 'ready' ? (
            <Result
              status="success"
              title="Датасет загружен"
              subTitle={
                <Space direction="vertical" size={0}>
                  <span>Событий: {dataset.total_events}</span>
                  <span>Кейсов: {dataset.total_cases}</span>
                  <span>Уникальных операций: {dataset.unique_activities}</span>
                </Space>
              }
            />
          ) : (
            <Result
              status="error"
              title="Ошибка обработки"
              subTitle={dataset.error_message ?? 'Не удалось обработать файл.'}
            />
          )}
        </div>
      )}
    </Modal>
  );
}
