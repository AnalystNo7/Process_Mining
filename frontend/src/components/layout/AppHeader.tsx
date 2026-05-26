import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { Dropdown } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/stores/authStore';

function sectionTitle(pathname: string): string {
  if (pathname === '/' || pathname.startsWith('/projects')) {
    if (/\/dashboards\/[^/]+/.test(pathname)) return 'Дашборд';
    if (/\/virtual-datasets\/[^/]+/.test(pathname)) return 'Виртуальный датасет';
    return 'Проекты';
  }
  if (pathname === '/me') return 'Профиль';
  if (pathname.startsWith('/admin/users')) return 'Пользователи';
  if (pathname.startsWith('/admin/global-roles')) return 'Роли';
  if (pathname.startsWith('/admin/audit-log')) return 'Аудит';
  return '';
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || '?';
}

export function AppHeader() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const displayName = user?.full_name ?? user?.username ?? 'Пользователь';

  return (
    <header className="header">
      <div className="hdr-section-title">
        <h1>{sectionTitle(location.pathname)}</h1>
      </div>
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
        placement="bottomRight"
      >
        <button
          type="button"
          className="hdr-avatar"
          style={{
            background: 'transparent',
            border: 0,
            cursor: 'pointer',
            padding: '4px 8px',
            borderRadius: 8,
          }}
        >
          <span className="hdr-avatar-circle">{initials(displayName)}</span>
          <span className="hdr-avatar-name">{displayName}</span>
        </button>
      </Dropdown>
    </header>
  );
}
