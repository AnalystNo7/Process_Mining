from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.datasets import PhysicalDataset
from app.db.models.projects import Project
from app.db.models.users import User
from app.db.repositories.event_log import PostgresEventLogRepository
from app.domain.types import EventFilter

_BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)


async def _setup_dataset(db: AsyncSession) -> int:
    user = User(
        username="repo_user",
        full_name="Repo",
        role="analyst",
        is_active=True,
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    project = Project(name="Repo Project", created_by=user.id)
    db.add(project)
    await db.flush()
    dataset = PhysicalDataset(
        project_id=project.id,
        name="DS",
        file_name="f.xlsx",
        file_size_bytes=1,
        file_hash="hash",
        storage_path="path",
        column_mapping={},
        total_events=0,
        total_cases=0,
        unique_activities=0,
        health_status="good",
        health_report={},
        uploaded_by=user.id,
        status="ready",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset.id


def _events_df(n: int) -> pd.DataFrame:
    rows = [
        {
            "case_id": f"C{i % 100}",
            "activity": f"A{i % 10}",
            "timestamp_start": _BASE + timedelta(hours=i),
            "timestamp_end": _BASE + timedelta(hours=i, minutes=30),
            "resource": f"R{i % 5}",
            "department": f"D{i % 3}",
            "attributes": {"doc_type": "typeX"},
        }
        for i in range(n)
    ]
    return pd.DataFrame(rows)


async def test_bulk_insert_5k_rows(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    inserted = await repo.bulk_insert(dataset_id, _events_df(5000))
    assert inserted == 5000
    assert await repo.count_events(dataset_id) == 5000


async def test_get_case_events_returns_sorted_by_time(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    df = pd.DataFrame(
        [
            {
                "case_id": "CASE-1",
                "activity": "Late",
                "timestamp_start": _BASE + timedelta(hours=5),
                "timestamp_end": _BASE + timedelta(hours=6),
            },
            {
                "case_id": "CASE-1",
                "activity": "Early",
                "timestamp_start": _BASE + timedelta(hours=1),
                "timestamp_end": _BASE + timedelta(hours=2),
            },
        ]
    )
    await repo.bulk_insert(dataset_id, df)
    events = await repo.get_case_events(dataset_id, "CASE-1")
    assert [e.activity for e in events] == ["Early", "Late"]


async def test_get_unique_activities(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    await repo.bulk_insert(dataset_id, _events_df(50))
    activities = await repo.get_unique_activities(dataset_id)
    assert sorted(activities) == [f"A{i}" for i in range(10)]


async def test_filter_by_date_range(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    await repo.bulk_insert(dataset_id, _events_df(24))
    f = EventFilter(
        date_range=(_BASE + timedelta(hours=10), _BASE + timedelta(hours=20))
    )
    assert await repo.count_events(dataset_id, f) == 11


async def test_filter_by_attributes(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    await repo.bulk_insert(dataset_id, _events_df(10))
    matched = EventFilter(attributes_filter={"doc_type": ["typeX"]})
    unmatched = EventFilter(attributes_filter={"doc_type": ["typeY"]})
    assert await repo.count_events(dataset_id, matched) == 10
    assert await repo.count_events(dataset_id, unmatched) == 0


async def test_delete_by_dataset_removes_all(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    await repo.bulk_insert(dataset_id, _events_df(20))
    await repo.delete_by_dataset(dataset_id)
    assert await repo.count_events(dataset_id) == 0


async def test_load_to_dataframe(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    await repo.bulk_insert(dataset_id, _events_df(15))
    df = await repo.load_to_dataframe(dataset_id)
    assert len(df) == 15
    assert "own_duration_sec" in df.columns
    # 30-минутная операция → 1800 секунд (generated column).
    assert int(df["own_duration_sec"].iloc[0]) == 1800


async def test_get_events_by_dataset_streams_all(db_session) -> None:
    dataset_id = await _setup_dataset(db_session)
    repo = PostgresEventLogRepository(db_session)
    await repo.bulk_insert(dataset_id, _events_df(25))
    collected = [event async for event in repo.get_events_by_dataset(dataset_id, chunk_size=10)]
    assert len(collected) == 25
