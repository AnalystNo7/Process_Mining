import { apiClient } from './client';

export interface CytoscapeElement {
  data: Record<string, unknown>;
}

export interface DfgResponse {
  nodes: CytoscapeElement[];
  edges: CytoscapeElement[];
  start_activities: Record<string, number>;
  end_activities: Record<string, number>;
}

export interface VariantRow {
  trace: string[];
  n_cases: number;
  avg_duration_seconds: number;
  example_case_ids: string[];
}

export interface TopPathsResponse {
  total_cases: number;
  total_variants: number;
  top_n: number;
  covered_cases: number;
  coverage_pct: number;
  variants: VariantRow[];
}

export interface CaseSummary {
  case_id: string;
  n_events: number;
  n_unique_activities: number;
  duration_seconds: number;
  has_rework: boolean;
  start: string;
  end: string;
}

export interface CaseListResponse {
  items: CaseSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface CaseEvent {
  activity: string;
  timestamp_start: string;
  timestamp_end: string;
  resource: string | null;
  department: string | null;
  role: string | null;
  sojourn_seconds: number;
  is_repeat: boolean;
}

export interface CaseDetail {
  case_id: string;
  attributes: Record<string, unknown>;
  events: CaseEvent[];
  total_duration_seconds: number;
  has_rework: boolean;
  n_events: number;
}

function analyticsBase(projectId: number, vdId: number): string {
  return `/projects/${projectId}/virtual-datasets/${vdId}/analytics`;
}

export async function getDfg(
  projectId: number,
  vdId: number,
  params?: {
    activity_level?: string;
    min_edge_frequency_pct?: number;
    max_nodes?: number;
  }
): Promise<DfgResponse> {
  const { data } = await apiClient.get<DfgResponse>(
    `${analyticsBase(projectId, vdId)}/dfg`,
    { params }
  );
  return data;
}

export async function getTopPaths(
  projectId: number,
  vdId: number,
  n: number
): Promise<TopPathsResponse> {
  const { data } = await apiClient.get<TopPathsResponse>(
    `${analyticsBase(projectId, vdId)}/top-paths`,
    { params: { n } }
  );
  return data;
}

export async function listCases(
  projectId: number,
  vdId: number,
  params: { page: number; page_size: number }
): Promise<CaseListResponse> {
  const { data } = await apiClient.get<CaseListResponse>(
    `${analyticsBase(projectId, vdId)}/cases`,
    { params }
  );
  return data;
}

export async function getCaseDetail(
  projectId: number,
  vdId: number,
  caseId: string
): Promise<CaseDetail> {
  const { data } = await apiClient.get<CaseDetail>(
    `${analyticsBase(projectId, vdId)}/case/${encodeURIComponent(caseId)}`
  );
  return data;
}

export async function downloadBpmn(
  projectId: number,
  vdId: number,
  fileName: string
): Promise<void> {
  const response = await apiClient.get(`${analyticsBase(projectId, vdId)}/bpmn`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
