# T17: Производственный календарь РФ + workdays

## Цель
Точный расчёт рабочих часов/дней между двумя datetime с учётом календаря РФ (выходные + праздники + переносы).

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "Длительность в рабочих vs календарных днях"
- Библиотека `workalendar` (`Russia` class)

## DoD
- [ ] Класс `WorkdayCalculator` в `app/domain/mining/workday.py`.
- [ ] Методы: `is_working_day(date)`, `working_seconds(start, end, work_day_start, work_day_end)`, `add_working_days(start, n_days)`.
- [ ] Использует `workalendar.europe.Russia` для перечня выходных/праздников.
- [ ] Рабочий день по умолчанию: 09:00–18:00 МСК (configurable).
- [ ] Все datetime приводятся к МСК (Europe/Moscow) перед расчётом.
- [ ] Unit-тесты с конкретными датами (выходные, праздники, переходы день→ночь).

## Реализация

```python
from datetime import datetime, time, date, timedelta
from zoneinfo import ZoneInfo
from workalendar.europe import Russia

class WorkdayCalculator:
    def __init__(self):
        self.cal = Russia()
        self.tz = ZoneInfo("Europe/Moscow")
    
    def is_working_day(self, d: date) -> bool:
        return self.cal.is_working_day(d)
    
    def working_seconds(
        self,
        start: datetime,
        end: datetime,
        work_day_start: time = time(9, 0),
        work_day_end: time = time(18, 0),
    ) -> float:
        # Приводим к МСК
        if start.tzinfo is None:
            start = start.replace(tzinfo=self.tz)
        else:
            start = start.astimezone(self.tz)
        if end.tzinfo is None:
            end = end.replace(tzinfo=self.tz)
        else:
            end = end.astimezone(self.tz)
        
        if end <= start:
            return 0.0
        
        total_seconds = 0.0
        current = start
        while current.date() <= end.date():
            if self.is_working_day(current.date()):
                day_start = datetime.combine(current.date(), work_day_start, tzinfo=self.tz)
                day_end = datetime.combine(current.date(), work_day_end, tzinfo=self.tz)
                
                # Пересечение [day_start, day_end] и [current, end]
                effective_start = max(current, day_start)
                effective_end = min(end, day_end)
                
                if effective_end > effective_start:
                    total_seconds += (effective_end - effective_start).total_seconds()
            
            # Переход на следующий день
            current = datetime.combine(current.date() + timedelta(days=1), time(0, 0), tzinfo=self.tz)
        
        return total_seconds
    
    def add_working_days(self, start: date, n_days: int) -> date:
        d = start
        added = 0
        while added < n_days:
            d += timedelta(days=1)
            if self.is_working_day(d):
                added += 1
        return d
```

## Тесты
```python
def test_is_working_day():
    cal = WorkdayCalculator()
    assert cal.is_working_day(date(2025, 1, 9))  # четверг
    assert not cal.is_working_day(date(2025, 1, 11))  # суббота
    assert not cal.is_working_day(date(2025, 1, 1))  # Новый год
    assert not cal.is_working_day(date(2025, 5, 9))  # День Победы

def test_working_seconds_within_one_day():
    cal = WorkdayCalculator()
    # Четверг 9 января 2025, с 10:00 до 14:00 = 4 часа
    start = datetime(2025, 1, 9, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    end = datetime(2025, 1, 9, 14, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    assert cal.working_seconds(start, end) == 4 * 3600

def test_working_seconds_across_weekend():
    cal = WorkdayCalculator()
    # Пятница 10.01 17:00 — понедельник 13.01 10:00
    # Пятница: 17:00–18:00 = 1ч
    # Суббота, Воскресенье: 0
    # Понедельник: 09:00–10:00 = 1ч
    # Итого: 2 часа
    start = datetime(2025, 1, 10, 17, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    end = datetime(2025, 1, 13, 10, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    assert cal.working_seconds(start, end) == 2 * 3600

def test_add_working_days_skips_holidays():
    cal = WorkdayCalculator()
    # 30.12.2024 (понедельник) + 5 раб.дней:
    # 31.12 — рабочий, 01.01-08.01 — праздники, 09.01 — первый рабочий
    # → 31.12, 09.01, 10.01, 13.01, 14.01
    result = cal.add_working_days(date(2024, 12, 30), 5)
    assert result == date(2025, 1, 14)
```

## Acceptance
Расчёт SLA в рабочих днях возвращает результаты, не превышающие сравнение с известными контрольными случаями (зимние праздники, майские).
