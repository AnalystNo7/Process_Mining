import { apiClient } from './client';

export interface ProjectOwner {
  id: number;
  username: string;
  full_name: string | null;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_by: ProjectOwner;
  created_at: string;
  physical_datasets_count: number;
  virtual_datasets_count: number;
  dashboards_count: number;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectPayload {
  name: string;
  description?: string | null;
}

export async function listProjects(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<ProjectListResponse> {
  const { data } = await apiClient.get<ProjectListResponse>('/projects', { params });
  return data;
}

export async function getProject(id: number): Promise<Project> {
  const { data } = await apiClient.get<Project>(`/projects/${id}`);
  return data;
}

export async function createProject(payload: ProjectPayload): Promise<Project> {
  const { data } = await apiClient.post<Project>('/projects', payload);
  return data;
}

export async function updateProject(id: number, payload: ProjectPayload): Promise<Project> {
  const { data } = await apiClient.patch<Project>(`/projects/${id}`, payload);
  return data;
}

export async function deleteProject(id: number): Promise<void> {
  await apiClient.delete(`/projects/${id}`);
}
