import {
  ArrowLeftOutlined,
  CheckOutlined,
  EditOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Spin, Space } from 'antd';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import type { EventFilter } from '@/api/analytics';
import {
  deleteWidget,
  getDashboard,
  updateDashboard,
  updateDashboardLayout,
  type WidgetLayoutItem,
} from '@/api/dashboards';
import { getVirtualDataset } from '@/api/virtualDatasets';
import {
  DashboardTabs,
  DEFAULT_TAB_KEY,
} from '@/features/dashboards/DashboardTabs';
import { AddWidgetModal } from '@/features/widgets/AddWidgetModal';
import { OperationViewModeToggle } from '@/features/widgets/OperationViewModeToggle';
import { OverviewFilterPanel } from '@/features/widgets/OverviewFilterPanel';
import type { ActivityLevel } from '@/api/virtualDatasets';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

export function DashboardPage() {
  const params = useParams();
  const dashboardId = Number(params.dashboardId);
  const projectId = Number(params.projectId);
  const vdId = Number(params.vdId);
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<string>(DEFAULT_TAB_KEY);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => getDashboard(dashboardId),
  });

  const { data: vd } = useQuery({
    queryKey: ['vd', vdId],
    queryFn: () => getVirtualDataset(projectId, vdId),
    enabled: Number.isFinite(projectId) && Number.isFinite(vdId),
  });
  const vdName = vd?.name ?? 'Виртуальный датасет';

  // T47: глобальные фильтры дашборда передаются в богатую подвкладку
  // process.process (ProcessGraphTab embedded). На бэке хранятся в произвольном
  // формате (Record<string, unknown>) — кастуем к EventFilter (поля совместимы).
  const globalFilters = useMemo<EventFilter>(
    () => (dashboard?.global_filters ?? {}) as EventFilter,
    [dashboard?.global_filters],
  );

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
      void queryClient.invalidateQueries({ queryKey: ['widget-data'] });
    },
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const updateLayoutMutation = useMutation({
    mutationFn: (items: WidgetLayoutItem[]) =>
      updateDashboardLayout(dashboardId, items),
    onError: (error) => notifyError(getErrorMessage(error)),
  });

  const widgets = useMemo(() => dashboard?.widgets ?? [], [dashboard?.widgets]);

  const handleLayoutChange = (items: WidgetLayoutItem[]) => {
    if (!editing) return;
    updateLayoutMutation.mutate(items);
  };

  const toggleEditing = () => setEditing((v) => !v);

  return (
    <div>
      <Link to={`/projects/${params.projectId}/virtual-datasets/${params.vdId}`}>
        <Button type="link" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }}>
          К виртуальному датасету
        </Button>
      </Link>
      <div className="page-head">
        <div>
          <h1>{dashboard?.name ?? 'Дашборд'}</h1>
        </div>
        <div className="page-head-actions">
          <Space>
            {Number.isFinite(projectId) && Number.isFinite(vdId) ? (
              <OperationViewModeToggle
                projectId={projectId}
                vdId={vdId}
                value={
                  ((vd?.config?.activity_level as ActivityLevel) ?? 'raw')
                }
              />
            ) : null}
            <Button
              icon={editing ? <CheckOutlined /> : <EditOutlined />}
              type={editing ? 'primary' : 'default'}
              onClick={toggleEditing}
            >
              {editing ? 'Завершить редактирование' : 'Редактировать'}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAddOpen(true)}
            >
              Добавить виджет
            </Button>
          </Space>
        </div>
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
            <DashboardTabs
              widgets={widgets}
              editing={editing}
              onLayoutChange={handleLayoutChange}
              onDeleteWidget={deleteWidgetMutation.mutate}
              activeTab={activeTab}
              onActiveTabChange={setActiveTab}
              projectId={projectId}
              vdId={vdId}
              vdName={vdName}
              globalFilters={globalFilters}
            />
          </div>
        </div>
      )}

      <AddWidgetModal
        dashboardId={dashboardId}
        open={addOpen}
        onClose={() => setAddOpen(false)}
        defaultTab={activeTab}
      />
    </div>
  );
}
