import { apiClient } from './client';

export interface VirtualDatasetBrief {
  id: number;
  name: string;
  physical_dataset_id: number;
  created_by: number;
  created_at: string;
}

export interface VirtualDataset {
  id: number;
  project_id: number;
  physical_dataset_id: number;
  name: string;
  description: string | null;
  role_mapping_snapshot: Record<string, unknown>;
  sla_rules_snapshot: unknown[];
  config: Record<string, unknown>;
  cached_stats: Record<string, unknown> | null;
  created_by: number;
  created_at: string;
  is_personal: boolean;
}

export interface CreateVirtualDatasetPayload {
  name: string;
  description?: string | null;
  physical_dataset_id: number;
}

export async function listVirtualDatasets(
  projectId: number
): Promise<{ items: VirtualDatasetBrief[]; total: number }> {
  const { data } = await apiClient.get<{ items: VirtualDatasetBrief[]; total: number }>(
    `/projects/${projectId}/virtual-datasets`
  );
  return data;
}

export async function getVirtualDataset(
  projectId: number,
  vdId: number
): Promise<VirtualDataset> {
  const { data } = await apiClient.get<VirtualDataset>(
    `/projects/${projectId}/virtual-datasets/${vdId}`
  );
  return data;
}

export async function createVirtualDataset(
  projectId: number,
  payload: CreateVirtualDatasetPayload
): Promise<VirtualDataset> {
  const { data } = await apiClient.post<VirtualDataset>(
    `/projects/${projectId}/virtual-datasets`,
    payload
  );
  return data;
}

export async function deleteVirtualDataset(
  projectId: number,
  vdId: number
): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/virtual-datasets/${vdId}`);
}
