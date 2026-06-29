import dayjs from 'dayjs';

/** Форматирует ISO-дату в «ДД.ММ.ГГГГ ЧЧ:ММ». */
export function formatDateTime(value: string | null | undefined): string {
  return value ? dayjs(value).format('DD.MM.YYYY HH:mm') : '—';
}

/** Адаптивно форматирует длительность в секундах: до 2 старших единиц,
 * с секундами для коротких значений. Примеры: «12с», «45м 12с», «3ч 25м»,
 * «2д 3ч». null/NaN → «—». */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) {
    return '—';
  }
  const s = Math.round(seconds);
  if (s < 60) {
    return `${s}с`;
  }
  if (s < 3600) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return sec ? `${m}м ${sec}с` : `${m}м`;
  }
  if (s < 86400) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return m ? `${h}ч ${m}м` : `${h}ч`;
  }
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  return h ? `${d}д ${h}ч` : `${d}д`;
}
