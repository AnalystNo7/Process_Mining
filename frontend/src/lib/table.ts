/** T49: общие константы для AntD-таблиц.
 *
 * Селектор страницы 20/50/100/500 (как в Excel-таблицах внутренних
 * аналитических систем) применяется на «больших» таблицах. На малых
 * (≤30 строк) пагинация автоматически скрывается через hideOnSinglePage.
 * Сортировка двухсостоятельная: один клик → ASC, второй → DESC,
 * без «выключения» сортировки.
 */
import type { SortOrder } from 'antd/es/table/interface';

export const TABLE_PAGE_SIZE_OPTIONS = [20, 50, 100, 500] as const;
export const TABLE_PAGE_SIZE_OPTIONS_STR = TABLE_PAGE_SIZE_OPTIONS.map(String);
export const DEFAULT_PAGE_SIZE = 20;

/** Только 2 состояния клика по заголовку — ASC ↔ DESC. Передаётся в
 * Table.sortDirections. AntD ожидает массив SortOrder[]. */
export const TWO_STATE_SORT_DIRECTIONS: SortOrder[] = ['ascend', 'descend'];
