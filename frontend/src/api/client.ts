import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';

import { useAuthStore } from '@/stores/authStore';
import { notifyError } from '@/lib/notify';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const apiClient = axios.create({ baseURL: BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

let isRefreshing = false;
let pendingQueue: ((token: string) => void)[] = [];

function isAuthEndpoint(url: string | undefined): boolean {
  return !!url && (url.includes('/auth/login') || url.includes('/auth/refresh'));
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const status = error.response?.status;

    // Истёкший access-токен — пробуем обновить и повторить запрос один раз.
    if (status === 401 && original && !original._retry && !isAuthEndpoint(original.url)) {
      original._retry = true;
      if (isRefreshing) {
        return new Promise<AxiosResponse>((resolve, reject) => {
          pendingQueue.push((token: string) => {
            original.headers.set('Authorization', `Bearer ${token}`);
            apiClient(original).then(resolve).catch(reject);
          });
        });
      }
      isRefreshing = true;
      try {
        const newToken = await useAuthStore.getState().refresh();
        pendingQueue.forEach((cb) => cb(newToken));
        pendingQueue = [];
        original.headers.set('Authorization', `Bearer ${newToken}`);
        return await apiClient(original);
      } catch (refreshError) {
        pendingQueue = [];
        void useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (status && status >= 500) {
      notifyError('Ошибка сервера. Попробуйте позже.');
    } else if (!error.response) {
      notifyError('Нет связи с сервером.');
    }
    return Promise.reject(error);
  }
);
