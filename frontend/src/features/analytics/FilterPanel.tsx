import { Button, Card, DatePicker, Select, Slider, Space, Typography } from 'antd';
import type { Dayjs } from 'dayjs';
import { useState } from 'react';

import type { EventFilter, FilterOptionsResponse } from '@/api/analytics';

const { RangePicker } = DatePicker;

const REWORK_OPTIONS = [
  { value: 'all', label: 'Показать все процессы' },
  { value: 'with', label: 'С зацикленностью' },
  { value: 'without', label: 'Без зацикленности' },
];

const EPC_MIN = 1;
const EPC_MAX = 60;

interface DraftState {
  dates: [Dayjs, Dayjs] | null;
  departments: string[];
  roles: string[];
  resources: string[];
  activities: string[];
  epc: [number, number];
  durationDays: [number, number] | null;
  rework: 'all' | 'with' | 'without';
}

const DUR_MIN = 0;
const DUR_MAX = 365;

function emptyDraft(): DraftState {
  return {
    dates: null,
    departments: [],
    roles: [],
    resources: [],
    activities: [],
    epc: [EPC_MIN, EPC_MAX],
    durationDays: null,
    rework: 'all',
  };
}

function toFilter(draft: DraftState): EventFilter {
  const filter: EventFilter = {};
  if (draft.dates) {
    filter.date_range = {
      from: draft.dates[0].startOf('day').toISOString(),
      to: draft.dates[1].endOf('day').toISOString(),
    };
  }
  if (draft.departments.length) {
    filter.departments = draft.departments;
  }
  if (draft.roles.length) {
    filter.roles = draft.roles;
  }
  if (draft.resources.length) {
    filter.resources = draft.resources;
  }
  if (draft.activities.length) {
    filter.activities = draft.activities;
  }
  if (draft.epc[0] > EPC_MIN || draft.epc[1] < EPC_MAX) {
    filter.events_per_case = { min: draft.epc[0], max: draft.epc[1] };
  }
  if (draft.durationDays) {
    filter.case_duration = {
      min_days: draft.durationDays[0],
      max_days: draft.durationDays[1],
    };
  }
  if (draft.rework === 'with') {
    filter.with_rework = true;
  }
  if (draft.rework === 'without') {
    filter.with_rework = false;
  }
  return filter;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {label}
      </Typography.Text>
      <div style={{ marginTop: 4 }}>{children}</div>
    </div>
  );
}

export function FilterPanel({
  options,
  onApply,
}: {
  options?: FilterOptionsResponse;
  onApply: (filter: EventFilter) => void;
}) {
  const [draft, setDraft] = useState<DraftState>(emptyDraft);
  const patch = (next: Partial<DraftState>) => setDraft((prev) => ({ ...prev, ...next }));

  const toOptions = (values: string[] = []) =>
    values.map((value) => ({ value, label: value }));

  const reset = () => {
    const fresh = emptyDraft();
    setDraft(fresh);
    onApply(toFilter(fresh));
  };

  return (
    <Card size="small" title="Фильтры" style={{ width: 264, flexShrink: 0 }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Field label="Дата начала экземпляра">
          <RangePicker
            style={{ width: '100%' }}
            value={draft.dates}
            onChange={(value) =>
              patch({
                dates: value && value[0] && value[1] ? [value[0], value[1]] : null,
              })
            }
          />
        </Field>

        <Field label="Кол-во операций в пути">
          <Slider
            range
            min={EPC_MIN}
            max={EPC_MAX}
            value={draft.epc}
            onChange={(value) => patch({ epc: value as [number, number] })}
          />
        </Field>

        <Field label="Подразделения">
          <Select
            mode="multiple"
            allowClear
            placeholder="Все"
            style={{ width: '100%' }}
            maxTagCount="responsive"
            value={draft.departments}
            options={toOptions(options?.departments)}
            onChange={(value) => patch({ departments: value })}
          />
        </Field>

        <Field label="Роли">
          <Select
            mode="multiple"
            allowClear
            placeholder="Все"
            style={{ width: '100%' }}
            maxTagCount="responsive"
            value={draft.roles}
            options={toOptions(options?.roles)}
            onChange={(value) => patch({ roles: value })}
          />
        </Field>

        <Field label="Исполнители">
          <Select
            mode="multiple"
            allowClear
            placeholder="Все"
            style={{ width: '100%' }}
            maxTagCount="responsive"
            value={draft.resources}
            options={toOptions(options?.resources)}
            onChange={(value) => patch({ resources: value })}
          />
        </Field>

        <Field label="Операции">
          <Select
            mode="multiple"
            allowClear
            placeholder="Все"
            style={{ width: '100%' }}
            maxTagCount="responsive"
            value={draft.activities}
            options={toOptions(options?.activities)}
            onChange={(value) => patch({ activities: value })}
          />
        </Field>

        <Field label="Длительность кейса, дней">
          <Slider
            range
            min={DUR_MIN}
            max={DUR_MAX}
            value={draft.durationDays ?? [DUR_MIN, DUR_MAX]}
            onChange={(value) => patch({ durationDays: value as [number, number] })}
          />
        </Field>

        <Field label="Зацикленность">
          <Select
            style={{ width: '100%' }}
            value={draft.rework}
            options={REWORK_OPTIONS}
            onChange={(value) => patch({ rework: value })}
          />
        </Field>

        <Space>
          <Button type="primary" size="small" onClick={() => onApply(toFilter(draft))}>
            Применить
          </Button>
          <Button size="small" onClick={reset}>
            Сбросить
          </Button>
        </Space>
      </Space>
    </Card>
  );
}
