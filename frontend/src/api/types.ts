export type UserRole = 'admin' | 'analyst';

export interface User {
  id: number;
  username: string;
  full_name: string | null;
  email: string | null;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
