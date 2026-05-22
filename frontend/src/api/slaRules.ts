import { apiClient } from './client';

export type SlaUnit = 'workdays' | 'calendar_days' | 'workhours' | 'hours';

export interface SlaRule {
  id: number;
  project_id: number;
  role: string;
  operation_pattern: string;
  sla_value: number;
  sla_unit: SlaUnit;
  tolerance_hours: number;
  target_compliance_pct: number;
  effective_from: string;
  effective_until: string | null;
  description: string | null;
  created_at: string;
}

export interface SlaRuleCreatePayload {
  role: string;
  operation_pattern: string;
  sla_value: number;
  sla_unit: SlaUnit;
  tolerance_hours: number;
  target_compliance_pct: number;
  effective_from: string;
  effective_until?: string | null;
  description?: string | null;
}

export type SlaRuleUpdatePayload = Partial<SlaRuleCreatePayload>;

export async function listSlaRules(
  projectId: number
): Promise<{ items: SlaRule[]; total: number }> {
  const { data } = await apiClient.get<{ items: SlaRule[]; total: number }>(
    `/projects/${projectId}/sla-rules`
  );
  return data;
}

export async function createSlaRule(
  projectId: number,
  payload: SlaRuleCreatePayload
): Promise<SlaRule> {
  const { data } = await apiClient.post<SlaRule>(
    `/projects/${projectId}/sla-rules`,
    payload
  );
  return data;
}

export async function updateSlaRule(
  ruleId: number,
  payload: SlaRuleUpdatePayload
): Promise<SlaRule> {
  const { data } = await apiClient.patch<SlaRule>(`/sla-rules/${ruleId}`, payload);
  return data;
}

export async function deleteSlaRule(ruleId: number): Promise<void> {
  await apiClient.delete(`/sla-rules/${ruleId}`);
}
