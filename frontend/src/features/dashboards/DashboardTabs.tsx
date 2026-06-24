import { Empty, Tabs } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import GridLayout, { type Layout } from 'react-grid-layout';

import type { EventFilter } from '@/api/analytics';
import type { Widget, WidgetLayoutItem } from '@/api/dashboards';
import { CasesTab } from '@/features/analytics/CasesTab';
import { DatasetTab } from '@/features/analytics/DatasetTab';
import { ProcessGraphTab } from '@/features/analytics/ProcessGraphTab';
import { StandardMetricsTab } from '@/features/analytics/StandardMetricsTab';
import { WidgetCard } from '@/features/widgets/WidgetCard';

import {
  DEFAULT_TAB_KEY,
  STANDARD_PM_TABS,
  topKeyOf,
  type TopTabDef,
} from './standardPmTabs';

const GRID_COLS = 12;
const ROW_HEIGHT = 60;
const GRID_MARGIN: [number, number] = [16, 16];
const GRID_PADDING: [number, number] = [0, 0];

interface DashboardTabsProps {
  widgets: Widget[];
  editing: boolean;
  onLayoutChange: (items: WidgetLayoutItem[]) => void;
  onDeleteWidget: (widgetId: number) => void;
  activeTab: string;
  onActiveTabChange: (tab: string) => void;
  /** T47: контекст для богатой подвкладки `process.process` (ProcessGraphTab). */
  projectId: number;
  vdId: number;
  vdName: string;
  globalFilters?: EventFilter;
}

/**
 * Каркас вкладочного дашборда «Стандартный PM» (T41, REQ §6.7).
 *
 * Топ-вкладки: Стандартные метрики · Обзор · Процесс · Детали.
 * У «Процесса» и «Деталей» есть вложенные подвкладки. Виджеты распределены по
 * полю `widget.tab` (строка-ключ из standardPmTabs). На каждой подвкладке —
 * собственный GridLayout с независимой сеткой.
 */
export function DashboardTabs({
  widgets,
  editing,
  onLayoutChange,
  onDeleteWidget,
  activeTab,
  onActiveTabChange,
  projectId,
  vdId,
  vdName,
  globalFilters,
}: DashboardTabsProps) {
  // Берём корень активного ключа (`details.cases` → `details`); если ключ —
  // это листовая топ-вкладка (`overview`/`standard_metrics`), оставляем как есть.
  const activeTop = useMemo(() => topKeyOf(activeTab), [activeTab]);

  const handleTopChange = (key: string) => {
    const top = STANDARD_PM_TABS.find((t) => t.key === key);
    if (!top) return;
    if (top.subtabs && top.subtabs.length > 0) {
      // При переключении на топ-вкладку с подвкладками — берём первую подвкладку.
      // Если уже стояли на подвкладке этого же топа — оставляем выбор.
      const currentBelongs = top.subtabs.some((s) => s.key === activeTab);
      if (!currentBelongs) onActiveTabChange(top.subtabs[0].key);
    } else {
      onActiveTabChange(top.key);
    }
  };

  // T47: для подвкладки `process.process` рендерим богатый ProcessGraphTab
  // (embedded), а не обычный GridLayout — там панель путей, частотный фильтр,
  // таблица операций и динамика по месяцам.
  const renderSubtabContent = (tabKey: string) => {
    // T42: «Стандартные метрики» — кастомный компонент с 3 таблицами
    // предрассчитанных показателей (cached_stats + operations + распределение).
    if (tabKey === 'standard_metrics') {
      return (
        <StandardMetricsTab
          projectId={projectId}
          vdId={vdId}
          externalFilter={globalFilters}
        />
      );
    }
    if (tabKey === 'process.process') {
      return (
        <ProcessGraphTab
          projectId={projectId}
          vdId={vdId}
          vdName={vdName}
          embedded
          externalFilter={globalFilters}
        />
      );
    }
    // T44: подвкладки «Детали → Экземпляры» и «Детали → Датасет» рендерятся
    // готовыми компонентами (drill-down к событиям и сырой лог), а не сеткой.
    if (tabKey === 'details.cases') {
      return (
        <CasesTab projectId={projectId} vdId={vdId} externalFilter={globalFilters} />
      );
    }
    if (tabKey === 'details.dataset') {
      return (
        <DatasetTab projectId={projectId} vdId={vdId} externalFilter={globalFilters} />
      );
    }
    return (
      <TabGrid
        widgets={widgets}
        tabKey={tabKey}
        editing={editing}
        onLayoutChange={onLayoutChange}
        onDeleteWidget={onDeleteWidget}
      />
    );
  };

  const topItems = STANDARD_PM_TABS.map((top) => ({
    key: top.key,
    label: top.label,
    children: (
      <TabBody
        top={top}
        activeKey={activeTab}
        onActiveChange={onActiveTabChange}
        renderContent={renderSubtabContent}
      />
    ),
  }));

  return (
    <Tabs
      activeKey={activeTop}
      onChange={handleTopChange}
      items={topItems}
      destroyInactiveTabPane
    />
  );
}

interface TabBodyProps {
  top: TopTabDef;
  activeKey: string;
  onActiveChange: (key: string) => void;
  /** T47: рендер контента зависит от ключа подвкладки (часть подвкладок
   * показывает кастомные компоненты, например ProcessGraphTab). */
  renderContent: (tabKey: string) => React.ReactNode;
}

/** Тело топ-вкладки: либо рендерит контент напрямую, либо через подвкладки. */
function TabBody({ top, activeKey, onActiveChange, renderContent }: TabBodyProps) {
  if (!top.subtabs || top.subtabs.length === 0) {
    return <>{renderContent(top.key)}</>;
  }
  return (
    <Tabs
      activeKey={activeKey}
      onChange={onActiveChange}
      type="card"
      size="small"
      items={top.subtabs.map((sub) => ({
        key: sub.key,
        label: sub.label,
        children: activeKey === sub.key ? renderContent(sub.key) : null,
      }))}
      destroyInactiveTabPane
    />
  );
}

interface TabGridProps {
  widgets: Widget[];
  tabKey: string;
  editing: boolean;
  onLayoutChange: (items: WidgetLayoutItem[]) => void;
  onDeleteWidget: (widgetId: number) => void;
}

/** GridLayout одной (под)вкладки. Сетка независимая, флаш позиций — отложенный. */
function TabGrid({
  widgets,
  tabKey,
  editing,
  onLayoutChange,
  onDeleteWidget,
}: TabGridProps) {
  const [gridWidth, setGridWidth] = useState(1200);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const flushTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && Math.abs(w - gridWidth) > 1) setGridWidth(w);
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [gridWidth]);

  // При смене вкладки отменяем pending-флаш позиций (иначе он применится к
  // другой вкладке после ухода с неё).
  useEffect(() => {
    return () => {
      if (flushTimer.current !== null) {
        window.clearTimeout(flushTimer.current);
        flushTimer.current = null;
      }
    };
  }, [tabKey]);

  const tabWidgets = useMemo(
    () => widgets.filter((w) => w.tab === tabKey),
    [widgets, tabKey],
  );

  const layout: Layout[] = useMemo(
    () =>
      tabWidgets.map((w) => ({
        i: String(w.id),
        x: w.grid_x,
        y: w.grid_y,
        w: w.grid_width,
        h: w.grid_height,
        minW: 2,
        minH: 2,
      })),
    [tabWidgets],
  );

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
      onLayoutChange(items);
      flushTimer.current = null;
    }, 400);
  };

  return (
    <div ref={containerRef} style={{ minHeight: 200 }}>
      {tabWidgets.length === 0 ? (
        <Empty description="На этой вкладке пока нет виджетов" />
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
          {tabWidgets.map((widget) => (
            <div key={String(widget.id)}>
              <WidgetCard widget={widget} onDelete={onDeleteWidget} editing={editing} />
            </div>
          ))}
        </GridLayout>
      )}
    </div>
  );
}

export { DEFAULT_TAB_KEY };
