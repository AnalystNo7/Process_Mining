import {
  FileSearchOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ProjectOutlined,
  SafetyOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/stores/authStore';

interface NavItem {
  key: string;
  label: string;
  icon: React.ReactNode;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

export function AppSider({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);

  const groups: NavGroup[] = [
    {
      label: 'Основное',
      items: [
        { key: '/projects', label: 'Проекты', icon: <ProjectOutlined /> },
        { key: '/me', label: 'Профиль', icon: <UserOutlined /> },
      ],
    },
  ];

  if (user?.role === 'admin') {
    groups.push({
      label: 'Администрирование',
      items: [
        { key: '/admin/users', label: 'Пользователи', icon: <TeamOutlined /> },
        { key: '/admin/global-roles', label: 'Роли', icon: <SafetyOutlined /> },
        { key: '/admin/audit-log', label: 'Аудит', icon: <FileSearchOutlined /> },
      ],
    });
  }

  const isActive = (key: string) =>
    location.pathname === key || location.pathname.startsWith(`${key}/`);

  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <div className="sb-brand-logo" aria-hidden />
        <div className="sb-brand-text">
          <span className="sb-brand-title">Process Mining</span>
          <span className="sb-brand-sub">Аналитика процессов</span>
        </div>
      </div>

      <nav className="sb-nav" aria-label="Главная навигация">
        {groups.map((group) => (
          <div key={group.label}>
            <div className="sb-section-label">{group.label}</div>
            {group.items.map((item) => (
              <button
                key={item.key}
                type="button"
                className="sb-item"
                aria-current={isActive(item.key) ? 'page' : undefined}
                onClick={() => navigate(item.key)}
                title={collapsed ? item.label : undefined}
              >
                <span className="anticon" aria-hidden>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        ))}
      </nav>

      <button
        type="button"
        className="sb-collapse"
        onClick={onToggle}
        aria-label={collapsed ? 'Развернуть меню' : 'Свернуть меню'}
      >
        {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        {!collapsed && <span style={{ marginLeft: 8 }}>Свернуть</span>}
      </button>
    </aside>
  );
}
