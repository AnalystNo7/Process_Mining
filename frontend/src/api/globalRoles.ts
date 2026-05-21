import { apiClient } from './client';

export interface GlobalRoleTemplate {
  id: number;
  role_name: string;
  patterns: string[];
  sort_order: number;
  is_active: boolean;
  updated_at: string;
}

export interface GlobalRoleListResponse {
  items: GlobalRoleTemplate[];
  total: number;
}

export interface GlobalRolePayload {
  role_name: string;
  patterns: string[];
  sort_order: number;
  is_active: boolean;
}

export async function listGlobalRoles(): Promise<GlobalRoleListResponse> {
  const { data } = await apiClient.get<GlobalRoleListResponse>('/admin/global-role-templates');
  return data;
}

export async function createGlobalRole(
  payload: GlobalRolePayload
): Promise<GlobalRoleTemplate> {
  const { data } = await apiClient.post<GlobalRoleTemplate>(
    '/admin/global-role-templates',
    payload
  );
  return data;
}

export async function updateGlobalRole(
  id: number,
  payload: GlobalRolePayload
): Promise<GlobalRoleTemplate> {
  const { data } = await apiClient.put<GlobalRoleTemplate>(
    `/admin/global-role-templates/${id}`,
    payload
  );
  return data;
}

export async function deleteGlobalRole(id: number): Promise<void> {
  await apiClient.delete(`/admin/global-role-templates/${id}`);
}
