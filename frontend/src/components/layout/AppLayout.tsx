import { Layout } from 'antd';
import { Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { AppSider } from './AppSider';

export function AppLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Layout>
        <AppSider />
        <Layout.Content style={{ padding: 24, overflow: 'auto' }}>
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
