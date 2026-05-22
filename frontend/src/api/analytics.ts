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

export interface EventFilter {
  date_range?: { from: string; to: string };
  departments?: string[];
  roles?: string[];
  resources?: string[];
  activities?: string[];
  case_duration?: { min_days?: number; max_days?: number };
  events_per_case?: { min?: number; max?: number };
  with_rework?: boolean | null;
  case_ids?: string[];
}

export interface PathRow {
  index: number;
  trace: string[];
  n_cases: number;
  avg_duration_seconds: number;
  case_ids: string[];
}

export interface ProcessMapResponse {
  mode: string;
  nodes: CytoscapeElement[];
  edges: CytoscapeElement[];
  start_activities: Record<string, number>;
  end_activities: Record<string, number>;
  paths: PathRow[];
  total_cases: number;
  total_variants: number;
  top_n: number;
  covered_cases: number;
  coverage_pct: number;
}

export interface OperationSummaryRow {
  activity: string;
  n_cases: number;
  n_events: number;
  avg_own_duration_seconds: number;
  median_own_duration_seconds: number;
  avg_share_pct: number;
}

export interface OperationsResponse {
  items: OperationSummaryRow[];
}

export interface MonthlyDynamicsRow {
  month: string;
  n_events: number;
  n_cases: number;
  avg_sojourn_seconds: number;
}

export interface MonthlyDynamicsResponse {
  items: MonthlyDynamicsRow[];
}

export interface FilterOptionsResponse {
  departments: string[];
  roles: string[];
  resources: string[];
  activities: string[];
}

/** Сериализует EventFilter в JSON-строку для query-параметра `filters`.
 * Пустые поля отбрасываются; полностью пустой фильтр → undefined. */
export function serializeFilters(filter?: EventFilter): string | undefined {
  if (!filter) {
    return undefined;
  }
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(filter)) {
    if (value == null) {
      continue;
    }
    if (Array.isArray(value) && value.length === 0) {
      continue;
    }
    if (
      typeof value === 'object' &&
      !Array.isArray(value) &&
      Object.keys(value).length === 0
    ) {
      continue;
    }
    cleaned[key] = value;
  }
  return Object.keys(cleaned).length > 0 ? JSON.stringify(cleaned) : undefined;
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

export async function getProcessMap(
  projectId: number,
  vdId: number,
  params: {
    mode?: 'top_paths' | 'frequency';
    n?: number;
    activity_level?: string;
    min_edge_frequency_pct?: number;
    max_nodes?: number;
    filters?: EventFilter;
  } = {}
): Promise<ProcessMapResponse> {
  const { filters, ...rest } = params;
  const { data } = await apiClient.get<ProcessMapResponse>(
    `${analyticsBase(projectId, vdId)}/process-map`,
    { params: { ...rest, filters: serializeFilters(filters) } }
  );
  return data;
}

export async function getOperations(
  projectId: number,
  vdId: number,
  params: { activity_level?: string; filters?: EventFilter } = {}
): Promise<OperationsResponse> {
  const { filters, ...rest } = params;
  const { data } = await apiClient.get<OperationsResponse>(
    `${analyticsBase(projectId, vdId)}/operations`,
    { params: { ...rest, filters: serializeFilters(filters) } }
  );
  return data;
}

export async function getMonthlyDynamics(
  projectId: number,
  vdId: number,
  params: { activity?: string; filters?: EventFilter } = {}
): Promise<MonthlyDynamicsResponse> {
  const { filters, ...rest } = params;
  const { data } = await apiClient.get<MonthlyDynamicsResponse>(
    `${analyticsBase(projectId, vdId)}/monthly-dynamics`,
    { params: { ...rest, filters: serializeFilters(filters) } }
  );
  return data;
}

export async function getFilterOptions(
  projectId: number,
  vdId: number
): Promise<FilterOptionsResponse> {
  const { data } = await apiClient.get<FilterOptionsResponse>(
    `${analyticsBase(projectId, vdId)}/filter-options`
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
