import {
  ArrowLeftOutlined,
  CheckOutlined,
  EditOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Empty, Spin, Space } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import GridLayout, { type Layout } from 'react-grid-layout';
import { Link, useParams } from 'react-router-dom';

import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import {
  deleteWidget,
  getDashboard,
  updateDashboard,
  updateDashboardLayout,
  type WidgetLayoutItem,
} from '@/api/dashboards';
import { AddWidgetModal } from '@/features/widgets/AddWidgetModal';
import { OverviewFilterPanel } from '@/features/widgets/OverviewFilterPanel';
import { WidgetCard } from '@/features/widgets/WidgetCard';
import { getErrorMessage, notifyError, notifySuccess } from '@/lib/notify';

const GRID_COLS = 12;
const ROW_HEIGHT = 60;
const GRID_MARGIN: [number, number] = [16, 16];
const GRID_PADDING: [number, number] = [0, 0];

export function DashboardPage() {
  const params = useParams();
  const dashboardId = Number(params.dashboardId);
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [gridWidth, setGridWidth] = useState(1200);
  const gridContainerRef = useRef<HTMLDivElement | null>(null);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => getDashboard(dashboardId),
  });

  useEffect(() => {
    if (!gridContainerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && Math.abs(w - gridWidth) > 1) setGridWidth(w);
    });
    observer.observe(gridContainerRef.current);
    return () => observer.disconnect();
  }, [gridWidth]);

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
  const layout: Layout[] = useMemo(
    () =>
      widgets.map((w) => ({
        i: String(w.id),
        x: w.grid_x,
        y: w.grid_y,
        w: w.grid_width,
        h: w.grid_height,
        minW: 2,
        minH: 2,
      })),
    [widgets]
  );

  const flushTimer = useRef<number | null>(null);
  const handleLayoutChange = (next: Layout[]) => {
    if (!editing) return;
    const items: WidgetLayoutItem[] = next.map((l) => ({
      id: Number(l.i),
      grid_x: l.x,
      grid_y: l.y,
      grid_width: l.w,
      grid_height: l.h,
    }));
    if (flushTimer.current !== null) window.clearTimeout(flushTimer.current);
    flushTimer.current = window.setTimeout(() => {
      updateLayoutMutation.mutate(items);
    }, 400);
  };

  const toggleEditing = () => {
    if (editing && flushTimer.current !== null) {
      window.clearTimeout(flushTimer.current);
      flushTimer.current = null;
    }
    setEditing((v) => !v);
  };

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
          <div style={{ flex: 1, minWidth: 0 }} ref={gridContainerRef}>
            {widgets.length === 0 ? (
              <Empty description="На дашборде пока нет виджетов" />
            ) : (
              <GridLayout
                className="layout"
                cols={GRID_COLS}
                rowHeight={ROW_HEIGHT}
                margin={GRID_MARGIN}
                containerPadding={GRID_PADDING}
                width={gridWidth}
                layout={layout}
                isDraggable={editing}
                isResizable={editing}
                resizeHandles={['s', 'w', 'e', 'n', 'sw', 'nw', 'se', 'ne']}
                draggableHandle=".widget-drag-handle"
                onLayoutChange={handleLayoutChange}
                compactType="vertical"
              >
                {widgets.map((widget) => (
                  <div key={String(widget.id)}>
                    <WidgetCard
                      widget={widget}
                      onDelete={deleteWidgetMutation.mutate}
                      editing={editing}
                    />
                  </div>
                ))}
              </GridLayout>
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
