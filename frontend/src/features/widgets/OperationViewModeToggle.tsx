import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Segmented, Tooltip } from 'antd';

import { setViewMode, type ActivityLevel } from '@/api/virtualDatasets';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

/**
 * Глобальный переключатель отображения операций датасета:
 * «Как в датасете» (raw) ↔ «По разметке» (role). Сохраняется на VD и
 * перестраивает все дашборды и аналитику (инвалидация всех запросов).
 */
export function OperationViewModeToggle({
  projectId,
  vdId,
  value,
}: {
  projectId: number;
  vdId: number;
  value: ActivityLevel;
}) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (level: ActivityLevel) => setViewMode(projectId, vdId, level),
    onSuccess: (_data, level) => {
      notifySuccess(
        level === 'role'
          ? 'Операции показаны по разметке'
          : 'Операции показаны как в датасете',
      );
      // Перестроить всё: VD, дашборды, виджеты, аналитика.
      void queryClient.invalidateQueries();
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  return (
    <Tooltip title="Как показывать операции: как в физическом датасете или переименованными по разметке ролей">
      <Segmented
        value={value}
        onChange={(v) => mutation.mutate(v as ActivityLevel)}
        disabled={mutation.isPending}
        options={[
          { label: 'Как в датасете', value: 'raw' },
          { label: 'По разметке', value: 'role' },
        ]}
      />
    </Tooltip>
  );
}
