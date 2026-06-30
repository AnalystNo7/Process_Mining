/**
 * Адаптивная высота виджетов длительности под число операций.
 *
 * Виджеты длительности (теплокарта «Узкие места», боксплот, «работа/ожидание»)
 * показывают топ-N операций по оси Y. Чтобы строки не сжимались, высота графика
 * растёт пропорционально числу операций; карточка в дашборде (GridLayout) тоже
 * растёт — но до предела `MAX_OPS`, дальше тело карточки скроллит.
 */

// Высота строки одной операции (px) — комфортный шаг между подписями.
const OP_ROW_PX = 30;
// До скольких операций карточка растёт; сверх того — внутренний скролл.
const MAX_OPS = 25;
// Единица сетки GridLayout: rowHeight(60) + вертикальный margin(16).
const GRID_UNIT = 76;
// Шапка карточки виджета.
const CARD_HEADER_PX = 40;

// Базовая высота (оси/отступы/легенда), не зависящая от числа операций.
const BASE_PX: Record<string, number> = {
  // Теплокарта: снизу вертикальные подписи департаментов — нужен запас.
  duration_bottleneck_heatmap: 220,
  // Горизонтальный боксплот: снизу ось длительности.
  operation_durations_boxplot: 80,
  // Горизонтальные стэк-бары + легенда сверху/снизу.
  sojourn_vs_own: 90,
};

/** Типы виджетов длительности с адаптивной высотой под число операций. */
export const DURATION_ADAPTIVE_TYPES = new Set(Object.keys(BASE_PX));

/** Пиксельная высота графика под `nOps` операций (для явной высоты Plot). */
export function durationPlotHeight(type: string, nOps: number): number {
  const base = BASE_PX[type] ?? 80;
  return base + Math.max(1, nOps) * OP_ROW_PX;
}

/**
 * Высота ячейки GridLayout (в строках сетки) под `nOps` операций: растёт до
 * `MAX_OPS`, не опускается ниже `minRows` (дефолтной высоты виджета).
 */
export function durationGridRows(
  type: string,
  nOps: number,
  minRows: number,
): number {
  const capped = Math.min(Math.max(1, nOps), MAX_OPS);
  const px = durationPlotHeight(type, capped) + CARD_HEADER_PX;
  const rows = Math.ceil((px + 16) / GRID_UNIT);
  return Math.max(minRows, rows);
}
