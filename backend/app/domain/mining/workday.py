"""Расчёт рабочего времени с учётом производственного календаря РФ
(см. 02_DOMAIN_LOGIC.md)."""

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from workalendar.europe import Russia

_MSK = ZoneInfo("Europe/Moscow")
_WORK_DAY_START = time(9, 0)
_WORK_DAY_END = time(18, 0)
# 1 рабочий день = 8 рабочих часов (09:00–18:00 минус час обеда — условно).
WORK_HOURS_PER_DAY = 8.0


class WorkdayCalculator:
    """Календарь РФ: рабочие/выходные/праздничные дни, расчёт рабочего времени."""

    def __init__(self) -> None:
        self.cal: Any = Russia()
        self.tz = _MSK
        # Кэш проверки рабочего дня — расчёт SLA перебирает много дат.
        self._working_day_cache: dict[date, bool] = {}

    def is_working_day(self, day: date) -> bool:
        cached = self._working_day_cache.get(day)
        if cached is None:
            cached = bool(self.cal.is_working_day(day))
            self._working_day_cache[day] = cached
        return cached

    def _to_msk(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self.tz)
        return value.astimezone(self.tz)

    def working_seconds(
        self,
        start: datetime,
        end: datetime,
        work_day_start: time = _WORK_DAY_START,
        work_day_end: time = _WORK_DAY_END,
    ) -> float:
        """Рабочее время (сек) между двумя моментами: только рабочие дни РФ,
        только часы work_day_start..work_day_end. Время приводится к МСК."""
        start = self._to_msk(start)
        end = self._to_msk(end)
        if end <= start:
            return 0.0

        total = 0.0
        current = start
        while current.date() <= end.date():
            if self.is_working_day(current.date()):
                day_start = datetime.combine(current.date(), work_day_start, tzinfo=self.tz)
                day_end = datetime.combine(current.date(), work_day_end, tzinfo=self.tz)
                effective_start = max(current, day_start)
                effective_end = min(end, day_end)
                if effective_end > effective_start:
                    total += (effective_end - effective_start).total_seconds()
            current = datetime.combine(
                current.date() + timedelta(days=1), time(0, 0), tzinfo=self.tz
            )
        return total

    def working_hours(self, start: datetime, end: datetime) -> float:
        """Рабочее время между двумя моментами в часах."""
        return self.working_seconds(start, end) / 3600.0

    def add_working_days(self, start: date, n_days: int) -> date:
        """Возвращает дату через n рабочих дней после start."""
        result = start
        added = 0
        while added < n_days:
            result += timedelta(days=1)
            if self.is_working_day(result):
                added += 1
        return result
