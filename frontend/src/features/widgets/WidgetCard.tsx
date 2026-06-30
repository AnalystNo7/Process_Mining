import {
  DeleteOutlined,
  DragOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Empty,
  InputNumber,
  Popconfirm,
  Popover,
  Select,
  Spin,
} from 'antd';
import { useState } from 'react';

import { getWidgetData, updateWidget, type Widget } from '@/api/dashboards';
import { getErrorMessage, notifyError } from '@/lib/notify';

import { WidgetContent } from './WidgetContent';
import { getWidgetHint } from './widgetHints';

// Виджеты длительности с интерактивными меню «топ-N» и «ранжирование».
const DURATION_CONTROL_TYPES = new Set([
  'operation_durations_boxplot',
  'sojourn_vs_own',
  'duration_bottleneck_heatmap',
]);

const TOP_N_OPTIONS = [10, 15, 20, 30, 50].map((value) => ({
  value,
  label: `Топ-${value}`,
}));

const SORT_BY_OPTIONS = [
  { value: 'frequency', label: 'По частоте' },
  { value: 'duration', label: 'По длительности' },
];

// Теплокарта узких мест: статистика для цвета/ранжирования. Среднее полезно,
// когда медиана = 0 (много мгновенных событий start==end).
const STAT_OPTIONS = [
  { value: 'median', label: 'Медиана' },
  { value: 'mean', label: 'Среднее' },
];

export function WidgetCard({
  widget,
  onDelete,
  editing = false,
}: {
  widget: Widget;
  onDelete: (id: number) => void;
  editing?: boolean;
}) {
  const queryClient = useQueryClient();
  const hasControls = DURATION_CONTROL_TYPES.has(widget.widget_type);
  const isHeatmap = widget.widget_type === 'duration_bottleneck_heatmap';
  // CDF длительности кейсов: цель SLA (часы) редактируется прямо в шапке
  // карточки и сохраняется в config виджета (линия SLA на графике следует
  // за этим значением).
  const isCdf = widget.widget_type === 'case_duration_cdf';
  const defaultSlaHours =
    typeof widget.config.sla_target_hours === 'number'
      ? widget.config.sla_target_hours
      : 24;
  const [slaHours, setSlaHours] = useState<number>(defaultSlaHours);

  const slaMutation = useMutation({
    mutationFn: (hours: number) =>
      updateWidget(widget.id, {
        config: { ...widget.config, sla_target_hours: hours },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['widget-data', widget.id] });
      void queryClient.invalidateQueries({
        queryKey: ['dashboard', widget.dashboard_id],
      });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  // Сохраняем SLA только если значение изменилось (по blur/Enter, не на ввод).
  const commitSla = () => {
    if (slaHours != null && slaHours !== defaultSlaHours) {
      slaMutation.mutate(slaHours);
    }
  };
  // Дефолты меню берём из config виджета (топ-N и ранжирование). Для боксплота
  // и sojourn ранжирование по умолчанию — по частоте; у теплокарт — из config.
  const defaultLimit =
    typeof widget.config.limit === 'number' ? widget.config.limit : 15;
  const defaultSortBy =
    typeof widget.config.sort_by === 'string' ? widget.config.sort_by : 'frequency';
  const defaultStat =
    typeof widget.config.stat === 'string' ? widget.config.stat : 'median';
  const [limit, setLimit] = useState<number>(defaultLimit);
  const [sortBy, setSortBy] = useState<string>(defaultSortBy);
  const [stat, setStat] = useState<string>(defaultStat);

  const { data, isLoading, isError } = useQuery({
    queryKey: hasControls
      ? ['widget-data', widget.id, limit, sortBy, isHeatmap ? stat : null]
      : ['widget-data', widget.id],
    queryFn: () =>
      getWidgetData(
        widget.id,
        hasControls
          ? { limit, sort_by: sortBy, ...(isHeatmap ? { stat } : {}) }
          : undefined,
      ),
    // T43.1: при ошибке (таймаут, 500) не ретраим бесконечно — сразу
    // покажем Empty с сообщением, чтобы пользователь не сидел на <Spin />.
    retry: 1,
  });

  const hint = getWidgetHint(widget.widget_type, widget.config);

  return (
    <Card
      size="small"
      className="widget-card"
      title={
        <span
          className={editing ? 'widget-drag-handle' : undefined}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            cursor: editing ? 'move' : 'default',
            userSelect: 'none',
          }}
        >
          {editing ? <DragOutlined style={{ color: 'var(--ink-4)' }} /> : null}
          {widget.title}
          {hint ? (
            <Popover
              title={widget.title}
              content={<div style={{ maxWidth: 320 }}>{hint}</div>}
            >
              <QuestionCircleOutlined
                style={{ color: 'var(--ink-4)', cursor: 'help' }}
                // Клик/перетаскивание иконки не должно запускать drag карточки.
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
              />
            </Popover>
          ) : null}
        </span>
      }
      style={{
        width: '100%',
        height: '100%',
        outline: editing ? '1px dashed var(--gpc-blue)' : undefined,
      }}
      styles={{
        body: {
          height: 'calc(100% - 40px)',
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        },
      }}
      extra={
        isCdf || hasControls || editing ? (
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {isCdf ? (
              <span
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                // Клик/ввод в поле не должен запускать перетаскивание карточки.
                onMouseDown={(e) => e.stopPropagation()}
              >
                <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>SLA</span>
                <InputNumber
                  size="small"
                  min={0}
                  addonAfter="ч"
                  style={{ width: 110 }}
                  value={slaHours}
                  onChange={(value) => setSlaHours(value ?? 0)}
                  onBlur={commitSla}
                  onPressEnter={commitSla}
                />
              </span>
            ) : null}
            {hasControls ? (
              <>
                <Select
                  size="small"
                  value={limit}
                  onChange={setLimit}
                  options={TOP_N_OPTIONS}
                  style={{ width: 88 }}
                />
                <Select
                  size="small"
                  value={sortBy}
                  onChange={setSortBy}
                  options={SORT_BY_OPTIONS}
                  style={{ width: 150 }}
                />
                {isHeatmap ? (
                  <Select
                    size="small"
                    value={stat}
                    onChange={setStat}
                    options={STAT_OPTIONS}
                    style={{ width: 110 }}
                  />
                ) : null}
              </>
            ) : null}
            {editing ? (
              <Popconfirm
                title="Удалить виджет?"
                okText="Удалить"
                cancelText="Отмена"
                onConfirm={() => onDelete(widget.id)}
              >
                <Button type="text" size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ) : null}
          </span>
        ) : undefined
      }
    >
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : isError || !data ? (
        <Empty description="Не удалось загрузить данные" />
      ) : (
        <WidgetContent type={widget.widget_type} data={data} />
      )}
    </Card>
  );
}
