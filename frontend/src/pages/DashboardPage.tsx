import { ArrowLeftOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Empty, Spin, Typography } from 'antd';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { deleteWidget, getDashboard, updateDashboard } from '@/api/dashboards';
import { AddWidgetModal } from '@/features/widgets/AddWidgetModal';
import { OverviewFilterPanel } from '@/features/widgets/OverviewFilterPanel';
import { WidgetCard } from '@/features/widgets/WidgetCard';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

export function DashboardPage() {
  const params = useParams();
  const dashboardId = Number(params.dashboardId);
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => getDashboard(dashboardId),
  });

  const deleteWidgetMutation = useMutation({
    mutationFn: deleteWidget,
    onSuccess: () => {
      notifySuccess('Виджет удалён');
      void queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const updateFiltersMutation = useMutation({
    mutationFn: (filters: Record<string, unknown>) =>
      updateDashboard(dashboardId, { global_filters: filters }),
    onSuccess: () => {
      notifySuccess('Фильтры применены');
      void queryClient.invalidateQueries({ queryKey: ['dashboard', dashboardId] });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const widgets = [...(dashboard?.widgets ?? [])].sort(
    (a, b) => a.grid_y - b.grid_y || a.grid_x - b.grid_x
  );

  return (
    <div>
      <Link to={`/projects/${params.projectId}/virtual-datasets/${params.vdId}`}>
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          К виртуальному датасету
        </Button>
      </Link>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          margin: '8px 0 16px',
        }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          {dashboard?.name ?? 'Дашборд'}
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setAddOpen(true)}
        >
          Добавить виджет
        </Button>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <OverviewFilterPanel
            dashboard={dashboard}
            onApply={updateFiltersMutation.mutate}
            isApplying={updateFiltersMutation.isPending}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            {widgets.length === 0 ? (
              <Empty description="На дашборде пока нет виджетов" />
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(12, 1fr)',
                  gap: 16,
                  alignItems: 'start',
                }}
              >
                {widgets.map((widget) => (
                  <WidgetCard
                    key={widget.id}
                    widget={widget}
                    onDelete={deleteWidgetMutation.mutate}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <AddWidgetModal
        dashboardId={dashboardId}
        open={addOpen}
        onClose={() => setAddOpen(false)}
      />
    </div>
  );
}
