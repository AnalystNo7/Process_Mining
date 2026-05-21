import { apiClient } from './client';

export interface RoleMapping {
  id: number;
  project_id: number;
  version: number;
  name: string;
  mapping: Record<string, string>;
  roles: string[];
  created_at: string;
  updated_at: string;
}

export interface SuggestionItem {
  role: string;
  matched_pattern: string | null;
}

export interface SuggestResponse {
  suggestions: Record<string, SuggestionItem>;
  available_roles: string[];
}

export async function getCurrentMapping(projectId: number): Promise<RoleMapping> {
  const { data } = await apiClient.get<RoleMapping>(
    `/projects/${projectId}/role-mappings/current`
  );
  return data;
}

export async function suggestRoles(
  projectId: number,
  departments: string[]
): Promise<SuggestResponse> {
  const { data } = await apiClient.post<SuggestResponse>(
    `/projects/${projectId}/role-mappings/suggest`,
    { departments }
  );
  return data;
}

export async function updateMapping(
  projectId: number,
  payload: { mapping: Record<string, string>; roles: string[] }
): Promise<RoleMapping> {
  const { data } = await apiClient.put<RoleMapping>(
    `/projects/${projectId}/role-mappings/current`,
    payload
  );
  return data;
}
