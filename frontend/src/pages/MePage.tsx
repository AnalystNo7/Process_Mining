import { Card, Descriptions } from 'antd';

import { useAuthStore } from '@/stores/authStore';

export function MePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Профиль</h1>
          <div className="page-sub">Данные вашей учётной записи.</div>
        </div>
      </div>
      <Card className="card">
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
