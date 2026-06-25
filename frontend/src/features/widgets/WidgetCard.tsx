import { DeleteOutlined, DragOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Empty, Popconfirm, Spin } from 'antd';

import { getWidgetData, type Widget } from '@/api/dashboards';

import { WidgetContent } from './WidgetContent';

export function WidgetCard({
  widget,
  onDelete,
  editing = false,
}: {
  widget: Widget;
  onDelete: (id: number) => void;
  editing?: boolean;
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['widget-data', widget.id],
    queryFn: () => getWidgetData(widget.id),
    // T43.1: при ошибке (таймаут, 500) не ретраим бесконечно — сразу
    // покажем Empty с сообщением, чтобы пользователь не сидел на <Spin />.
    retry: 1,
  });

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
        editing ? (
          <Popconfirm
            title="Удалить виджет?"
            okText="Удалить"
            cancelText="Отмена"
            onConfirm={() => onDelete(widget.id)}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
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
