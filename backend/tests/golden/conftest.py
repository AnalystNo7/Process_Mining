import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.domain.mining.loading import load_event_log

GOLDEN_DIR = Path(__file__).parents[3] / "golden_data"

COLUMN_MAPPING = {
    "case_id": "doc_id",
    "activity": "Операция",
    "timestamp_start": "in_progress_datetime",
    "timestamp_end": "completed_datetime",
    "resource": "task_user",
    "department": "task_user_department",
}


@pytest.fixture(scope="session")
def synthetic_log() -> pd.DataFrame:
    """Эталонный журнал событий (synthetic_log.xlsx), загруженный без дедупликации.

    Метрики в expected_metrics.json вычислены именно на этом наборе."""
    return load_event_log(GOLDEN_DIR / "synthetic_log.xlsx", COLUMN_MAPPING)


@pytest.fixture(scope="session")
def expected_metrics() -> dict[str, Any]:
    with open(GOLDEN_DIR / "expected_metrics.json", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data
