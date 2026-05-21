import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import * as authApi from '@/api/auth';
import type { User } from '@/api/types';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  login: (username: string, password: string, useLdap?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<string>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      login: async (username, password, useLdap = false) => {
        const resp = await authApi.login({ username, password, use_ldap: useLdap });
        set({
          accessToken: resp.access_token,
          refreshToken: resp.refresh_token,
          user: resp.user,
        });
      },

      logout: async () => {
        const rt = get().refreshToken;
        if (rt) {
          try {
            await authApi.logout(rt);
          } catch {
            // Локальное состояние очищаем в любом случае.
          }
        }
        set({ accessToken: null, refreshToken: null, user: null });
      },

      refresh: async () => {
        const rt = get().refreshToken;
        if (!rt) {
          throw new Error('Нет refresh-токена');
        }
        const resp = await authApi.refresh(rt);
        set({
          accessToken: resp.access_token,
          refreshToken: resp.refresh_token,
          user: resp.user,
        });
        return resp.access_token;
      },
    }),
    { name: 'pm-auth' }
  )
);
