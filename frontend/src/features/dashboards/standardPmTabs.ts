// T41 — каркас вкладочного дашборда «Стандартный PM» из REQ §6.7.
// Ключи синхронизированы с backend (services/dashboard_service.py::STANDARD_PM_TAB_KEYS).
// Подвкладки именуются через точку: process.duration, details.cases и т.п.
// Виджеты в БД хранят `tab` строкой по этой же таксономии.

export interface SubTabDef {
  key: string;
  label: string;
  // Если виджеты этой подвкладки строятся вокруг графа процесса — фронт может
  // подсветить особую раскладку. Сейчас это нужно только подвкладкам Процесса.
  hasProcessGraph?: boolean;
}

export interface TopTabDef {
  key: string;
  label: string;
  subtabs?: SubTabDef[];
}

export const STANDARD_PM_TABS: TopTabDef[] = [
  {
    key: 'standard_metrics',
    label: 'Стандартные метрики',
  },
  {
    key: 'overview',
    label: 'Обзор',
  },
  {
    key: 'process',
    label: 'Процесс',
    subtabs: [
      { key: 'process.process', label: 'Процесс', hasProcessGraph: true },
      { key: 'process.duration', label: 'Длительность', hasProcessGraph: true },
      { key: 'process.rework', label: 'Зацикленность', hasProcessGraph: true },
      { key: 'process.paths', label: 'Метрики путей' },
      { key: 'process.distribution', label: 'Распределение по времени' },
    ],
  },
  {
    key: 'details',
    label: 'Детали',
    subtabs: [
      { key: 'details.cases', label: 'Экземпляры' },
      { key: 'details.operations', label: 'Операции' },
      { key: 'details.dataset', label: 'Датасет' },
    ],
  },
];

export const DEFAULT_TAB_KEY = 'overview';

// Полный список листовых ключей (то, что хранится в widget.tab).
export const ALL_TAB_KEYS: readonly string[] = STANDARD_PM_TABS.flatMap((top) =>
  top.subtabs ? top.subtabs.map((s) => s.key) : [top.key],
);

// Подпись для произвольного листового ключа.
export function tabLabel(key: string): string {
  for (const top of STANDARD_PM_TABS) {
    if (top.key === key && !top.subtabs) return top.label;
    if (top.subtabs) {
      const sub = top.subtabs.find((s) => s.key === key);
      if (sub) return `${top.label} → ${sub.label}`;
    }
  }
  return key;
}

// Определяет корневой ключ топ-вкладки по ключу листа.
export function topKeyOf(key: string): string {
  const dot = key.indexOf('.');
  return dot === -1 ? key : key.slice(0, dot);
}
