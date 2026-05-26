import { Button, Card, DatePicker, Form, Radio, Segmented, Slider, Space } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useMemo, useState } from 'react';

import type { Dashboard } from '@/api/dashboards';

type Rework = 'all' | 'with' | 'without';
type Granularity = 'D' | 'W' | 'M' | 'Q';

interface FilterState {
  eventsRange: [number, number];
  rework: Rework;
  granularity: Granularity;
  dateRange: [Dayjs | null, Dayjs | null];
}

const EVENTS_MIN = 1;
const EVENTS_MAX = 200;
const DEFAULT_STATE: FilterState = {
  eventsRange: [EVENTS_MIN, EVENTS_MAX],
  rework: 'all',
  granularity: 'M',
  dateRange: [null, null],
};

function readState(dashboard: Dashboard | undefined): FilterState {
  const gf = (dashboard?.global_filters ?? {}) as Record<string, unknown>;
  const epc = gf.events_per_case as { min?: number; max?: number } | undefined;
  const dr = gf.date_range as { from?: string; to?: string } | undefined;
  const wr = gf.with_rework as boolean | null | undefined;
  const gran = String(gf.granularity ?? 'M').toUpperCase() as Granularity;
  return {
    eventsRange: [epc?.min ?? EVENTS_MIN, epc?.max ?? EVENTS_MAX],
    rework: wr === true ? 'with' : wr === false ? 'without' : 'all',
    granularity: (['D', 'W', 'M', 'Q'] as const).includes(gran) ? gran : 'M',
    dateRange: [dr?.from ? dayjs(dr.from) : null, dr?.to ? dayjs(dr.to) : null],
  };
}

function toGlobalFilters(state: FilterState): Record<string, unknown> {
  const result: Record<string, unknown> = { granularity: state.granularity };
  if (state.eventsRange[0] > EVENTS_MIN || state.eventsRange[1] < EVENTS_MAX) {
    result.events_per_case = { min: state.eventsRange[0], max: state.eventsRange[1] };
  }
  if (state.rework !== 'all') {
    result.with_rework = state.rework === 'with';
  }
  const [from, to] = state.dateRange;
  if (from && to) {
    result.date_range = { from: from.toISOString(), to: to.toISOString() };
  }
  return result;
}

export function OverviewFilterPanel({
  dashboard,
  onApply,
  isApplying,
}: {
  dashboard: Dashboard | undefined;
  onApply: (filters: Record<string, unknown>) => void;
  isApplying: boolean;
}) {
  const initial = useMemo(() => readState(dashboard), [dashboard]);
  const [state, setState] = useState<FilterState>(initial);

  const apply = () => onApply(toGlobalFilters(state));
  const reset = () => {
    setState(DEFAULT_STATE);
    onApply(toGlobalFilters(DEFAULT_STATE));
  };

  return (
    <Card
      size="small"
      title="Фильтры"
      className="card"
      style={{ width: 280, flexShrink: 0 }}
    >
      <Form layout="vertical" size="small">
        <Form.Item label="Кол-во операций в пути" style={{ marginBottom: 16 }}>
          <Slider
            range
            min={EVENTS_MIN}
            max={EVENTS_MAX}
            value={state.eventsRange}
            onChange={(v) =>
              setState((s) => ({ ...s, eventsRange: v as [number, number] }))
            }
          />
        </Form.Item>
        <Form.Item label="Последовательность">
          <Button disabled style={{ width: '100%' }}>
            Настройки
          </Button>
        </Form.Item>
        <Form.Item label="Зацикленность">
          <Radio.Group
            value={state.rework}
            onChange={(e) => setState((s) => ({ ...s, rework: e.target.value }))}
            optionType="default"
            style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
          >
            <Radio value="all">Показать все процессы</Radio>
            <Radio value="with">Только с повторами</Radio>
            <Radio value="without">Без повторов</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item label="Гранулярность">
          <Segmented
            block
            value={state.granularity}
            onChange={(v) =>
              setState((s) => ({ ...s, granularity: v as Granularity }))
            }
            options={[
              { label: 'День', value: 'D' },
              { label: 'Неделя', value: 'W' },
              { label: 'Месяц', value: 'M' },
              { label: 'Квартал', value: 'Q' },
            ]}
          />
        </Form.Item>
        <Form.Item label="Дата начала экземпляра">
          <DatePicker.RangePicker
            value={state.dateRange}
            onChange={(v) =>
              setState((s) => ({
                ...s,
                dateRange: (v ?? [null, null]) as [Dayjs | null, Dayjs | null],
              }))
            }
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button type="primary" loading={isApplying} onClick={apply}>
            Применить
          </Button>
          <Button onClick={reset}>Сбросить</Button>
        </Space>
      </Form>
    </Card>
  );
}
