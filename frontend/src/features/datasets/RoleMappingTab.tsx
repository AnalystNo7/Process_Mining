import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Empty,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd';
import { AxiosError } from 'axios';
import { useEffect, useState } from 'react';

import { getCurrentMapping, suggestRoles, updateMapping } from '@/api/roleMappings';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

const UNMAPPED = 'Не размечено';

interface MappingRow {
  department: string;
  role: string;
}

export function RoleMappingTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [roleOptions, setRoleOptions] = useState<string[]>([]);

  const { data: mapping, isLoading, error } = useQuery({
    queryKey: ['role-mapping', projectId],
    queryFn: () => getCurrentMapping(projectId),
    retry: false,
  });

  useEffect(() => {
    if (mapping) {
      setDraft({ ...mapping.mapping });
      setRoleOptions(
        Array.from(
          new Set([...mapping.roles, ...Object.values(mapping.mapping), UNMAPPED])
        ).sort()
      );
    }
  }, [mapping]);

  const suggestMutation = useMutation({
    mutationFn: () => suggestRoles(projectId, Object.keys(draft)),
    onSuccess: (data) => {
      setDraft((prev) => {
        const next = { ...prev };
        for (const [dept, item] of Object.entries(data.suggestions)) {
          next[dept] = item.role;
        }
        return next;
      });
      setRoleOptions((prev) =>
        Array.from(new Set([...prev, ...data.available_roles])).sort()
      );
      notifySuccess('Роли подобраны автоматически');
    },
    onError: (e) => notifyError(getErrorMessage(e)),
  });

  const saveMutation = useMutation({
    mutationFn: () => updateMapping(projectId, { mapping: draft, roles: roleOptions }),
    onSuccess: () => {
      notifySuccess('Разметка ролей сохранена');
      void queryClient.invalidateQueries({ queryKey: ['role-mapping', projectId] });
    },
    onError: (e) => notifyError(getErrorMessage(e)),
  });

  if (error instanceof AxiosError && error.response?.status === 404) {
    return (
      <Empty description="Загрузите физический датасет — подразделения для разметки появятся автоматически." />
    );
  }

  const rows: MappingRow[] = Object.keys(draft)
    .sort()
    .map((department) => ({ department, role: draft[department] }));
  const unmappedCount = rows.filter((r) => !r.role || r.role === UNMAPPED).length;

  const columns: TableColumnsType<MappingRow> = [
    { title: 'Подразделение', dataIndex: 'department', key: 'department' },
    {
      title: 'Роль',
      key: 'role',
      width: 320,
      render: (_, row) => (
        <Select
          showSearch
          style={{ width: 300 }}
          value={row.role || undefined}
          placeholder="Выберите роль"
          options={roleOptions.map((r) => ({ value: r, label: r }))}
          onChange={(value) =>
            setDraft((prev) => ({ ...prev, [row.department]: value }))
          }
        />
      ),
    },
  ];

  return (
    <div>
      <Typography.Paragraph type="secondary">
        Разметка сопоставляет подразделения из журнала ролям. Сохранение создаёт
        новую версию — существующие виртуальные датасеты не меняются.
      </Typography.Paragraph>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button
          onClick={() => suggestMutation.mutate()}
          loading={suggestMutation.isPending}
          disabled={rows.length === 0}
        >
          Автоподбор ролей
        </Button>
        <Button
          type="primary"
          onClick={() => saveMutation.mutate()}
          loading={saveMutation.isPending}
          disabled={rows.length === 0}
        >
          Сохранить разметку
        </Button>
        <Tag>Подразделений: {rows.length}</Tag>
        <Tag color={unmappedCount > 0 ? 'orange' : 'green'}>
          Не размечено: {unmappedCount}
        </Tag>
        {mapping && <Tag>Версия: {mapping.version}</Tag>}
      </Space>
      <Table
        rowKey="department"
        loading={isLoading}
        columns={columns}
        dataSource={rows}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
      />
    </div>
  );
}
