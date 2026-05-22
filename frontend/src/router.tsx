import { Spin } from 'antd';
import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AppLayout } from '@/components/layout/AppLayout';
import { LoginPage } from '@/features/auth/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

const ProjectsPage = lazy(() =>
  import('@/pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage }))
);
const ProjectDetailPage = lazy(() =>
  import('@/pages/ProjectDetailPage').then((m) => ({ default: m.ProjectDetailPage }))
);
const VirtualDatasetPage = lazy(() =>
  import('@/pages/VirtualDatasetPage').then((m) => ({ default: m.VirtualDatasetPage }))
);
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage }))
);
const MePage = lazy(() => import('@/pages/MePage').then((m) => ({ default: m.MePage })));
const AdminUsersPage = lazy(() =>
  import('@/pages/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage }))
);
const AuditLogPage = lazy(() =>
  import('@/pages/AuditLogPage').then((m) => ({ default: m.AuditLogPage }))
);
const GlobalRolesPage = lazy(() =>
  import('@/pages/GlobalRolesPage').then((m) => ({ default: m.GlobalRolesPage }))
);

function PageFallback() {
  return (
    <div style={{ textAlign: 'center', padding: 64 }}>
      <Spin size="large" />
    </div>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/projects" replace />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
            <Route
              path="/projects/:projectId/virtual-datasets/:vdId"
              element={<VirtualDatasetPage />}
            />
            <Route
              path="/projects/:projectId/virtual-datasets/:vdId/dashboards/:dashboardId"
              element={<DashboardPage />}
            />
            <Route path="/me" element={<MePage />} />
            <Route element={<ProtectedRoute adminOnly />}>
              <Route path="/admin/users" element={<AdminUsersPage />} />
              <Route path="/admin/audit-log" element={<AuditLogPage />} />
              <Route path="/admin/global-roles" element={<GlobalRolesPage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
