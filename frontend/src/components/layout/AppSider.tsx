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
        <div className="sb-brand-cube" aria-hidden>
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M12 2 3 7v10l9 5 9-5V7l-9-5Zm0 2.3 6.8 3.78L12 11.85 5.2 8.08 12 4.3ZM5 9.7l6.25 3.47v6.96L5 16.66V9.7Zm14 0v6.96l-6.25 3.47v-6.96L19 9.7Z"
              fill="#fff"
            />
          </svg>
        </div>
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
