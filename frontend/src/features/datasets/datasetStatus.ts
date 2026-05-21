/** Метки и цвета статусов физического датасета и health-проверок. */

export const DATASET_STATUS_LABEL: Record<string, string> = {
  validating: 'Обработка',
  ready: 'Готов',
  failed: 'Ошибка',
};

export const DATASET_STATUS_COLOR: Record<string, string> = {
  validating: 'processing',
  ready: 'green',
  failed: 'red',
};

export const HEALTH_LABEL: Record<string, string> = {
  good: 'В норме',
  warning: 'Предупреждения',
  critical: 'Критические проблемы',
};

export const HEALTH_COLOR: Record<string, string> = {
  good: 'green',
  warning: 'orange',
  critical: 'red',
};

export const SEVERITY_COLOR: Record<string, string> = {
  info: 'blue',
  warning: 'orange',
  critical: 'red',
};

export function isTerminalStatus(status: string): boolean {
  return status === 'ready' || status === 'failed';
}
