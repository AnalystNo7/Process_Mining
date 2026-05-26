import { apiClient } from './client';

export interface Widget {
  id: number;
  dashboard_id: number;
  widget_type: string;
  title: string;
  config: Record<string, unknown>;
  local_filters: Record<string, unknown> | null;
  use_global_filters: boolean;
  grid_x: number;
  grid_y: number;
  grid_width: number;
  grid_height: number;
}

export interface Dashboard {
  id: number;
  virtual_dataset_id: number;
  name: string;
  description: string | null;
  global_filters: Record<string, unknown>;
  applied_slice_id: number | null;
  layout: unknown[];
  created_by: number;
  created_at: string;
  widgets: Widget[];
}

export interface DashboardBrief {
  id: number;
  name: string;
  created_by: number;
  created_at: string;
}

export interface WidgetCreatePayload {
  widget_type: string;
  title: string;
  config?: Record<string, unknown>;
  grid_width?: number;
  grid_height?: number;
}

export async function listDashboards(
  projectId: number,
  vdId: number
): Promise<{ items: DashboardBrief[]; total: number }> {
  const { data } = await apiClient.get<{ items: DashboardBrief[]; total: number }>(
    `/projects/${projectId}/virtual-datasets/${vdId}/dashboards`
  );
  return data;
}

export async function createDashboard(
  projectId: number,
  vdId: number,
  payload: { name: string; description?: string | null }
): Promise<Dashboard> {
  const { data } = await apiClient.post<Dashboard>(
    `/projects/${projectId}/virtual-datasets/${vdId}/dashboards`,
    payload
  );
  return data;
}

export async function getDashboard(dashboardId: number): Promise<Dashboard> {
  const { data } = await apiClient.get<Dashboard>(`/dashboards/${dashboardId}`);
  return data;
}

export async function deleteDashboard(dashboardId: number): Promise<void> {
  await apiClient.delete(`/dashboards/${dashboardId}`);
}

export async function updateDashboard(
  dashboardId: number,
  payload: {
    name?: string;
    description?: string | null;
    global_filters?: Record<string, unknown>;
  }
): Promise<Dashboard> {
  const { data } = await apiClient.patch<Dashboard>(
    `/dashboards/${dashboardId}`,
    payload
  );
  return data;
}

export async function addWidget(
  dashboardId: number,
  payload: WidgetCreatePayload
): Promise<Widget> {
  const { data } = await apiClient.post<Widget>(
    `/dashboards/${dashboardId}/widgets`,
    payload
  );
  return data;
}

export async function deleteWidget(widgetId: number): Promise<void> {
  await apiClient.delete(`/widgets/${widgetId}`);
}

export interface WidgetLayoutItem {
  id: number;
  grid_x: number;
  grid_y: number;
  grid_width: number;
  grid_height: number;
}

export async function updateDashboardLayout(
  dashboardId: number,
  items: WidgetLayoutItem[]
): Promise<Dashboard> {
  const { data } = await apiClient.patch<Dashboard>(
    `/dashboards/${dashboardId}/widgets/layout`,
    { widgets: items }
  );
  return data;
}

export async function getWidgetData(
  widgetId: number
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>(
    `/widgets/${widgetId}/data`
  );
  return data;
}
