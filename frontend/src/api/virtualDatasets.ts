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

export type ActivityLevel = 'raw' | 'role';

/** Глобальный режим отображения операций датасета (raw — как в физ. датасете,
 * role — по разметке). Перестраивает все дашборды и аналитику. */
export async function setViewMode(
  projectId: number,
  vdId: number,
  activity_level: ActivityLevel
): Promise<VirtualDataset> {
  const { data } = await apiClient.patch<VirtualDataset>(
    `/projects/${projectId}/virtual-datasets/${vdId}/view-mode`,
    { activity_level }
  );
  return data;
}

/** Применяет текущую разметку ролей ко всем датасетам проекта (после
 * сохранения разметки): обновляет снимок и включает режим role. */
export async function applyMappingToView(
  projectId: number
): Promise<{ updated_virtual_datasets: number }> {
  const { data } = await apiClient.post<{ updated_virtual_datasets: number }>(
    `/projects/${projectId}/virtual-datasets/apply-mapping-view`
  );
  return data;
}
