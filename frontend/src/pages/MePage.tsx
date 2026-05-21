import { Card, Descriptions, Typography } from 'antd';

import { useAuthStore } from '@/stores/authStore';

export function MePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div>
      <Typography.Title level={3}>Профиль</Typography.Title>
      <Card>
        <Descriptions column={1}>
          <Descriptions.Item label="Логин">{user?.username ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="ФИО">{user?.full_name ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Email">{user?.email ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Роль">
            {user?.role === 'admin' ? 'Администратор' : 'Аналитик'}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
