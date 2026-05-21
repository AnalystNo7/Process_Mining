import { apiClient } from './client';
import type { UserRole } from './types';

export interface AppUser {
  id: number;
  username: string;
  full_name: string | null;
  email: string | null;
  role: UserRole;
  is_ldap: boolean;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface UserListResponse {
  items: AppUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserCreatePayload {
  username: string;
  full_name?: string | null;
  email?: string | null;
  role: UserRole;
  is_ldap: boolean;
  password?: string | null;
}

export interface UserUpdatePayload {
  full_name?: string | null;
  email?: string | null;
  role?: UserRole;
  is_active?: boolean;
  password?: string | null;
}

export async function listUsers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<UserListResponse> {
  const { data } = await apiClient.get<UserListResponse>('/users', { params });
  return data;
}

export async function createUser(payload: UserCreatePayload): Promise<AppUser> {
  const { data } = await apiClient.post<AppUser>('/users', payload);
  return data;
}

export async function updateUser(id: number, payload: UserUpdatePayload): Promise<AppUser> {
  const { data } = await apiClient.patch<AppUser>(`/users/${id}`, payload);
  return data;
}

export async function deleteUser(id: number): Promise<void> {
  await apiClient.delete(`/users/${id}`);
}
