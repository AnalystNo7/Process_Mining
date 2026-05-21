import {
  FileSearchOutlined,
  ProjectOutlined,
  SafetyOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Layout, Menu, type MenuProps } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/stores/authStore';

export function AppSider() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);

  const items: NonNullable<MenuProps['items']> = [
    { key: '/projects', icon: <ProjectOutlined />, label: 'Проекты' },
    { key: '/me', icon: <UserOutlined />, label: 'Профиль' },
  ];

  if (user?.role === 'admin') {
    items.push({
      key: 'admin',
      icon: <SafetyOutlined />,
      label: 'Администрирование',
      children: [
        { key: '/admin/users', icon: <TeamOutlined />, label: 'Пользователи' },
        { key: '/admin/global-roles', icon: <SafetyOutlined />, label: 'Роли' },
        { key: '/admin/audit-log', icon: <FileSearchOutlined />, label: 'Аудит' },
      ],
    });
  }

  return (
    <Layout.Sider theme="light" width={220}>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        defaultOpenKeys={['admin']}
        items={items}
        onClick={(info) => navigate(info.key)}
        style={{ height: '100%', borderRight: 0 }}
      />
    </Layout.Sider>
  );
}
