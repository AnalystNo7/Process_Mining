import { notification } from 'antd';
import { AxiosError } from 'axios';

/** Извлекает человекочитаемое сообщение об ошибке из ответа API. */
export function getErrorMessage(error: unknown, fallback = 'Произошла ошибка'): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }
  return fallback;
}

export function notifyError(message: string): void {
  notification.error({ message });
}

export function notifySuccess(message: string): void {
  notification.success({ message });
}
