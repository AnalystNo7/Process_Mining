import dayjs from 'dayjs';

/** Форматирует ISO-дату в «ДД.ММ.ГГГГ ЧЧ:ММ». */
export function formatDateTime(value: string | null | undefined): string {
  return value ? dayjs(value).format('DD.MM.YYYY HH:mm') : '—';
}
