import dayjs from 'dayjs';

/** Форматирует ISO-дату в «ДД.ММ.ГГГГ ЧЧ:ММ». */
export function formatDateTime(value: string | null | undefined): string {
  return value ? dayjs(value).format('DD.MM.YYYY HH:mm') : '—';
}

/** Форматирует длительность в секундах в «Xд Yч Zм». */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) {
    return '—';
  }
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return days > 0 ? `${days}д ${hours}ч ${minutes}м` : `${hours}ч ${minutes}м`;
}
