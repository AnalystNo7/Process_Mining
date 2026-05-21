import { apiClient } from './client';

export interface ColumnInfo {
  name: string;
  sample_values: string[];
  dtype: string;
}

export interface PreviewResponse {
  columns: ColumnInfo[];
  preview_rows: Record<string, unknown>[];
  total_rows: number;
  suggested_mapping: Record<string, string>;
  preview_token: string;
}

export interface PhysicalDataset {
  id: number;
  project_id: number;
  name: string;
  file_name: string;
  file_size_bytes: number;
  status: string;
  total_events: number;
  total_cases: number;
  unique_activities: number;
  period_start: string | null;
  period_end: string | null;
  health_status: string;
  health_report: Record<string, unknown>;
  column_mapping: Record<string, string>;
  uploaded_at: string;
  error_message: string | null;
}

export interface HealthCheckItem {
  name: string;
  severity: string;
  message: string;
  value: unknown;
}

export interface HealthReport {
  status: string;
  checks: HealthCheckItem[];
}

export interface UploadTaskResponse {
  id: number;
  status: string;
  task_id: string | null;
}

export interface CreateDatasetPayload {
  name: string;
  preview_token: string;
  column_mapping: Record<string, string>;
  save_as_template: boolean;
}

export async function previewDataset(
  projectId: number,
  file: File
): Promise<PreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<PreviewResponse>(
    `/projects/${projectId}/physical-datasets/preview`,
    formData
  );
  return data;
}

export async function createDataset(
  projectId: number,
  payload: CreateDatasetPayload
): Promise<UploadTaskResponse> {
  const { data } = await apiClient.post<UploadTaskResponse>(
    `/projects/${projectId}/physical-datasets`,
    payload
  );
  return data;
}

export async function listDatasets(
  projectId: number
): Promise<{ items: PhysicalDataset[]; total: number }> {
  const { data } = await apiClient.get<{ items: PhysicalDataset[]; total: number }>(
    `/projects/${projectId}/physical-datasets`
  );
  return data;
}

export async function getDataset(
  projectId: number,
  datasetId: number
): Promise<PhysicalDataset> {
  const { data } = await apiClient.get<PhysicalDataset>(
    `/projects/${projectId}/physical-datasets/${datasetId}`
  );
  return data;
}

export async function getDatasetHealth(
  projectId: number,
  datasetId: number
): Promise<HealthReport> {
  const { data } = await apiClient.get<HealthReport>(
    `/projects/${projectId}/physical-datasets/${datasetId}/health`
  );
  return data;
}

export async function deleteDataset(
  projectId: number,
  datasetId: number
): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/physical-datasets/${datasetId}`);
}
