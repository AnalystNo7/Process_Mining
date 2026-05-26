import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { AppSider } from './AppSider';

const STORAGE_KEY = 'gpc:sidebar:collapsed';

export function AppLayout() {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  return (
    <div className="app" data-sidebar={collapsed ? 'collapsed' : 'expanded'}>
      <AppSider collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      <AppHeader />
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
