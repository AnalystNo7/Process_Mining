"""build_stats: режим операций (raw vs role) влияет на метрики операций."""
from datetime import datetime, timezone

import pandas as pd

from app.domain.mining.role_mapping import apply_role_mapping

# build_stats импортируется лениво внутри тестов: модуль app.tasks.compute_stats
# тянет celery→settings, поэтому импорт на уровне модуля сломал бы сбор тестов
# в окружении без .env (домены ниже от settings не зависят).


def _ts(day: int, hour: int) -> datetime:
    return datetime(2025, 1, day, hour, 0, tzinfo=timezone.utc)


def _df() -> pd.DataFrame:
    # Имена операций содержат департамент. Две операции отличаются только им:
    # «Согласование Отдел А» и «Согласование Отдел Б». При разметке оба отдела
    # → роль «Согласующий», поэтому операции сворачиваются в одну.
    rows = [
        {"case_id": "C1", "activity": "Согласование Отдел А",
         "department": "Отдел А", "resource": "U1",
         "timestamp_start": _ts(1, 9), "timestamp_end": _ts(1, 10)},
        {"case_id": "C1", "activity": "Согласование Отдел Б",
         "department": "Отдел Б", "resource": "U2",
         "timestamp_start": _ts(1, 11), "timestamp_end": _ts(1, 12)},
        {"case_id": "C2", "activity": "Согласование Отдел А",
         "department": "Отдел А", "resource": "U1",
         "timestamp_start": _ts(2, 9), "timestamp_end": _ts(2, 10)},
    ]
    df = pd.DataFrame(rows)
    df["own_duration_sec"] = (
        df["timestamp_end"] - df["timestamp_start"]
    ).dt.total_seconds()
    return apply_role_mapping(df, {"Отдел А": "Согласующий", "Отдел Б": "Согласующий"})


def test_role_level_collapses_unique_activities() -> None:
    from app.tasks.compute_stats import build_stats

    df = _df()
    raw = build_stats(df, "activity")
    role = build_stats(df, "activity_with_role")
    # raw: «Согласование Отдел А», «Согласование Отдел Б» → 2 операции.
    assert raw["unique_activities"] == 2
    # role: обе → «Согласование Согласующий» → 1 операция.
    assert role["unique_activities"] == 1
    # Метрики, не зависящие от операции, не меняются.
    assert raw["total_events"] == role["total_events"] == 3
    assert raw["total_cases"] == role["total_cases"] == 2


def test_default_activity_col_is_raw() -> None:
    from app.tasks.compute_stats import build_stats

    df = _df()
    assert build_stats(df)["unique_activities"] == 2
