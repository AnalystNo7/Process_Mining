# T08: Каркас React-фронтенда

## Цель
Полноценный каркас фронтенда: AntD, роутинг, API-клиент, страница логина, layout, защищённые роуты, базовые сторы.

## Контекст
- `04_UI.md` весь файл (особенно "Общий layout", "Login", "Список проектов")
- `03_API.md` раздел "1. Аутентификация"

## DoD
- [ ] Структура `frontend/src/` согласно `00_OVERVIEW.md`.
- [ ] React Router с роутами `/login`, `/projects`, `/me`, `/admin/*` (заглушки).
- [ ] AntD `ConfigProvider` с `ruRU` локалью.
- [ ] dayjs настроен на русский.
- [ ] API-клиент на axios с автоматической подстановкой Bearer-токена и refresh при 401.
- [ ] Zustand-стор `useAuthStore` хранит токены и user, persist в localStorage.
- [ ] React Query QueryClient настроен.
- [ ] Страница `/login` работает: вызывает API, сохраняет токены, редирект на `/projects`.
- [ ] Защищённые роуты редиректят на `/login` если нет токена.
- [ ] Layout с Sider, Header (username + logout), Content + Outlet.
- [ ] Хлебные крошки в Header (заглушка).
- [ ] Ошибки API показываются через `notification.error`.

## Реализация

### Структура файлов
```
src/
├── api/
│   ├── client.ts              ← axios instance с interceptors
│   ├── auth.ts                ← login, refresh, logout, me
│   └── types.ts               ← TypeScript интерфейсы из 03_API.md
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx
│   │   ├── AppSider.tsx
│   │   └── AppHeader.tsx
│   ├── ProtectedRoute.tsx
│   └── ErrorBoundary.tsx
├── features/
│   └── auth/
│       └── LoginPage.tsx
├── pages/
│   ├── ProjectsPage.tsx       ← пока заглушка
│   ├── AdminUsersPage.tsx     ← пока заглушка
│   └── NotFoundPage.tsx
├── stores/
│   └── authStore.ts
├── router.tsx
└── main.tsx
```

### `src/api/client.ts`
```ts
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let queue: ((token: string) => void)[] = [];

apiClient.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      if (isRefreshing) {
        return new Promise((resolve) => {
          queue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          });
        });
      }
      isRefreshing = true;
      try {
        const refreshed = await useAuthStore.getState().refresh();
        queue.forEach((cb) => cb(refreshed));
        queue = [];
        original.headers.Authorization = `Bearer ${refreshed}`;
        return apiClient(original);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
```

### `src/stores/authStore.ts`
```ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as authApi from '@/api/auth';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  login: (username: string, password: string, useLdap?: boolean) => Promise<void>;
  logout: () => void;
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
        set({ accessToken: resp.access_token, refreshToken: resp.refresh_token, user: resp.user });
      },
      logout: () => {
        const rt = get().refreshToken;
        if (rt) authApi.logout(rt).catch(() => {});
        set({ accessToken: null, refreshToken: null, user: null });
      },
      refresh: async () => {
        const rt = get().refreshToken;
        if (!rt) throw new Error('No refresh token');
        const resp = await authApi.refresh(rt);
        set({ accessToken: resp.access_token, refreshToken: resp.refresh_token });
        return resp.access_token;
      },
    }),
    { name: 'auth' }
  )
);
```

### `src/components/ProtectedRoute.tsx`
```tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

export function ProtectedRoute({ adminOnly = false }: { adminOnly?: boolean }) {
  const { accessToken, user } = useAuthStore();
  const location = useLocation();
  if (!accessToken) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (adminOnly && user?.role !== 'admin') return <Navigate to="/projects" replace />;
  return <Outlet />;
}
```

### `src/router.tsx`
Используя `createBrowserRouter` или Routes:
```tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route element={<ProtectedRoute />}>
    <Route element={<AppLayout />}>
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/projects" element={<ProjectsPage />} />
      <Route path="/me" element={<MePage />} />
      <Route element={<ProtectedRoute adminOnly />}>
        <Route path="/admin/users" element={<AdminUsersPage />} />
        <Route path="/admin/audit-log" element={<AuditLogPage />} />
        <Route path="/admin/global-roles" element={<GlobalRolesPage />} />
      </Route>
    </Route>
  </Route>
  <Route path="*" element={<NotFoundPage />} />
</Routes>
```

## Тесты
- Unit-тест authStore (login/logout/persist).
- Vitest на LoginPage: ввод credentials → mock API → редирект.

## Acceptance
Открыть http://localhost:5173 → редирект на /login → залогиниться → видна страница /projects с layout. Logout возвращает на /login.
