import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Dropdown, Layout, Space } from 'antd';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/stores/authStore';

export function AppHeader() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <Layout.Header
      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
    >
      <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>Process Mining</div>
      <Space>
        <Dropdown
          menu={{
            items: [
              {
                key: 'profile',
                icon: <UserOutlined />,
                label: 'Профиль',
                onClick: () => navigate('/me'),
              },
              {
                key: 'logout',
                icon: <LogoutOutlined />,
                label: 'Выйти',
                onClick: handleLogout,
              },
            ],
          }}
        >
          <Button type="text" icon={<UserOutlined />} style={{ color: '#fff' }}>
            {user?.full_name ?? user?.username ?? 'Пользователь'}
          </Button>
        </Dropdown>
      </Space>
    </Layout.Header>
  );
}
