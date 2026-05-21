import { DeleteOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Empty, Popconfirm, Spin } from 'antd';

import { getWidgetData, type Widget } from '@/api/dashboards';

import { WidgetContent } from './WidgetContent';

export function WidgetCard({
  widget,
  onDelete,
}: {
  widget: Widget;
  onDelete: (id: number) => void;
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['widget-data', widget.id],
    queryFn: () => getWidgetData(widget.id),
  });

  const span = Math.min(Math.max(widget.grid_width, 3), 12);

  return (
    <Card
      size="small"
      title={widget.title}
      style={{ gridColumn: `span ${span}` }}
      extra={
        <Popconfirm
          title="Удалить виджет?"
          okText="Удалить"
          cancelText="Отмена"
          onConfirm={() => onDelete(widget.id)}
        >
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
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
