import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { LoginPage } from '@/features/auth/LoginPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { AuditLogPage } from '@/pages/AuditLogPage';
import { GlobalRolesPage } from '@/pages/GlobalRolesPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { MePage } from '@/pages/MePage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ProjectDetailPage } from '@/pages/ProjectDetailPage';
import { ProjectsPage } from '@/pages/ProjectsPage';
import { VirtualDatasetPage } from '@/pages/VirtualDatasetPage';

export function AppRouter() {
  return (
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
  );
}
