from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.domain.mining.workday import WorkdayCalculator

_MSK = ZoneInfo("Europe/Moscow")


def test_is_working_day() -> None:
    cal = WorkdayCalculator()
    assert cal.is_working_day(date(2025, 1, 9))  # четверг
    assert not cal.is_working_day(date(2025, 1, 11))  # суббота
    assert not cal.is_working_day(date(2025, 1, 1))  # Новый год
    assert not cal.is_working_day(date(2025, 5, 9))  # День Победы


def test_working_seconds_within_one_day() -> None:
    cal = WorkdayCalculator()
    start = datetime(2025, 1, 9, 10, 0, tzinfo=_MSK)
    end = datetime(2025, 1, 9, 14, 0, tzinfo=_MSK)
    assert cal.working_seconds(start, end) == 4 * 3600


def test_working_seconds_across_weekend() -> None:
    cal = WorkdayCalculator()
    # Пятница 17:00 → понедельник 10:00: пт 17–18 (1ч) + пн 9–10 (1ч) = 2ч.
    start = datetime(2025, 1, 10, 17, 0, tzinfo=_MSK)
    end = datetime(2025, 1, 13, 10, 0, tzinfo=_MSK)
    assert cal.working_seconds(start, end) == 2 * 3600


def test_working_seconds_zero_when_end_before_start() -> None:
    cal = WorkdayCalculator()
    start = datetime(2025, 1, 9, 14, 0, tzinfo=_MSK)
    end = datetime(2025, 1, 9, 10, 0, tzinfo=_MSK)
    assert cal.working_seconds(start, end) == 0.0


def test_working_seconds_naive_treated_as_msk() -> None:
    cal = WorkdayCalculator()
    start = datetime(2025, 1, 9, 10, 0)
    end = datetime(2025, 1, 9, 12, 0)
    assert cal.working_seconds(start, end) == 2 * 3600


def test_add_working_days_skips_holidays() -> None:
    cal = WorkdayCalculator()
    # 30.12.2024 + 5 рабочих дней: 31.12, затем праздники 01–08.01,
    # рабочие 09.01, 10.01, 13.01, 14.01.
    assert cal.add_working_days(date(2024, 12, 30), 5) == date(2025, 1, 14)


def test_working_hours() -> None:
    cal = WorkdayCalculator()
    start = datetime(2025, 1, 9, 9, 0, tzinfo=_MSK)
    end = datetime(2025, 1, 9, 17, 0, tzinfo=_MSK)
    assert cal.working_hours(start, end) == 8.0
