import { apiClient } from './client';

export interface AuditUser {
  id: number;
  username: string;
}

export interface AuditEntry {
  id: number;
  user: AuditUser | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditListResponse {
  items: AuditEntry[];
  total: number;
  page: number;
  page_size: number;
}

export async function listAuditLog(params: {
  page: number;
  page_size: number;
  action?: string;
  entity_type?: string;
}): Promise<AuditListResponse> {
  const { data } = await apiClient.get<AuditListResponse>('/admin/audit-log', { params });
  return data;
}
