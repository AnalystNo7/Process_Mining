import { apiClient } from './client';

export type AnnotationTargetType = 'node' | 'edge' | 'case' | 'time_range';

export interface Annotation {
  id: number;
  virtual_dataset_id: number;
  target_type: AnnotationTargetType;
  target: Record<string, unknown>;
  text: string;
  color: string | null;
  author_id: number;
  author_name: string;
  created_at: string;
  updated_at: string;
}

export interface AnnotationCreatePayload {
  target_type: AnnotationTargetType;
  target: Record<string, unknown>;
  text: string;
  color?: string | null;
}

export async function listAnnotations(
  vdId: number,
  targetType?: AnnotationTargetType
): Promise<{ items: Annotation[]; total: number }> {
  const { data } = await apiClient.get<{ items: Annotation[]; total: number }>(
    `/virtual-datasets/${vdId}/annotations`,
    { params: targetType ? { target_type: targetType } : undefined }
  );
  return data;
}

export async function createAnnotation(
  vdId: number,
  payload: AnnotationCreatePayload
): Promise<Annotation> {
  const { data } = await apiClient.post<Annotation>(
    `/virtual-datasets/${vdId}/annotations`,
    payload
  );
  return data;
}

export async function updateAnnotation(
  annotationId: number,
  text: string
): Promise<Annotation> {
  const { data } = await apiClient.put<Annotation>(`/annotations/${annotationId}`, {
    text,
  });
  return data;
}

export async function deleteAnnotation(annotationId: number): Promise<void> {
  await apiClient.delete(`/annotations/${annotationId}`);
}
