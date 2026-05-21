# 06. Стратегия тестирования

## Цели тестирования

1. **Корректность алгоритмов process mining.** Главный риск — незаметные ошибки в формулах метрик. Защита: golden tests против эталонных цифр.
2. **Работоспособность API.** Endpoints возвращают ожидаемые статусы и схемы.
3. **Целостность данных.** Миграции БД накатываются и откатываются.
4. **UI-функциональность.** Базовые сценарии работают (опционально, в MVP — не приоритет).

## Уровни тестов

| Уровень          | Технологии                       | Цель                                                            |
|------------------|----------------------------------|------------------------------------------------------------------|
| Unit             | pytest                           | Чистые функции домена (алгоритмы, валидация, маппинг)            |
| Golden           | pytest                           | Алгоритмы против эталонных цифр на синтетическом датасете        |
| Integration      | pytest + httpx + test_db         | API эндпоинты с реальной БД                                      |
| E2E (опционально)| Playwright                       | UI-сценарии: вход, создание проекта, загрузка, просмотр дашборда |

## Структура тестов

```
backend\tests\
├── unit\
│   ├── domain\
│   │   ├── mining\
│   │   │   ├── test_loading.py
│   │   │   ├── test_health.py
│   │   │   ├── test_role_mapping.py
│   │   │   ├── test_duration.py
│   │   │   ├── test_rework.py
│   │   │   ├── test_variants.py
│   │   │   ├── test_graph.py
│   │   │   ├── test_sla.py
│   │   │   ├── test_resources.py
│   │   │   ├── test_dynamics.py
│   │   │   └── test_filters.py
│   │   └── test_workday_calculator.py
│   ├── services\
│   │   └── test_*.py
│   └── core\
│       └── test_security.py
├── golden\
│   ├── conftest.py                ← фикстура загрузки synthetic_log.xlsx
│   └── test_golden_metrics.py     ← главные regression-тесты
├── integration\
│   ├── conftest.py                ← test DB, test client
│   ├── api\
│   │   ├── test_auth.py
│   │   ├── test_projects.py
│   │   ├── test_physical_datasets.py
│   │   ├── test_virtual_datasets.py
│   │   ├── test_analytics.py
│   │   ├── test_dashboards.py
│   │   └── test_admin.py
│   └── repositories\
│       └── test_event_log_repository.py
└── pytest.ini
```

## Golden Tests — детально

Это **самая важная** часть тестов. Они гарантируют, что цифры, которые видит аналитик, корректны.

### Принципы

1. **Источник истины:** `golden_data/synthetic_log.xlsx` (обезличенный фрагмент реального лога TESSA).
2. **Эталоны:** `golden_data/expected_metrics.json` (заранее вычислены, проверены на оригинальном датасете против отчётов Газпром ЦПС).
3. **Tolerance:** `±1%` для float-значений (учитывает погрешности floating-point), **точное совпадение** для int.
4. **Запускаются на каждом PR** в CI, плюс перед релизом.

### Структура `expected_metrics.json`

См. `golden_data/expected_metrics.json` (уже сгенерирован).

Содержит:
- `basic_kpi`: total_cases (1328), total_events (25606), unique_activities (507), period_start/end.
- `case_duration`: avg_with_rework_seconds, avg_without_rework_seconds, n_cases_with/without_rework.
- `rework_global`: total_operations, total_repeats, global_rework_pct (20.06%).
- `top10_operations_by_volume`: топ-10 операций с rework_pct.
- `process_metrics`: unique_traces, variability_pct (89.83%), mean_occurrence_pct (3.04%).
- `events_per_case_distribution`: min/max/median/mean/p90/p95.
- `top10_departments_by_events`.
- `sojourn_time_top10_operations`: для каждой топ-операции — avg/median/p90 секунд.

### Пример golden test

```python
# tests/golden/test_golden_metrics.py
import json
import pytest
from pathlib import Path
import pandas as pd
from app.domain.mining import loading, rework, variants, duration

GOLDEN_DIR = Path(__file__).parent.parent.parent.parent / "golden_data"

@pytest.fixture(scope="session")
def synthetic_log() -> pd.DataFrame:
    """Загружает синтетический лог как стандартизованный DataFrame."""
    column_mapping = {
        "case_id": "doc_id",
        "activity": "Операция",
        "timestamp_start": "in_progress_datetime",
        "timestamp_end": "completed_datetime",
        "resource": "task_user",
        "department": "task_user_department",
    }
    return loading.load_event_log(
        GOLDEN_DIR / "synthetic_log.xlsx",
        column_mapping,
    )

@pytest.fixture(scope="session")
def expected_metrics() -> dict:
    with open(GOLDEN_DIR / "expected_metrics.json", encoding="utf-8") as f:
        return json.load(f)


class TestGoldenMetrics:
    """Regression-тесты против эталонных метрик."""

    def test_basic_kpi(self, synthetic_log, expected_metrics):
        """KPI: количество кейсов, событий, уникальных операций."""
        exp = expected_metrics["basic_kpi"]
        assert synthetic_log["case_id"].nunique() == exp["total_cases"]
        assert len(synthetic_log) == exp["total_events"]
        assert synthetic_log["activity"].nunique() == exp["unique_activities"]

    def test_global_rework_pct(self, synthetic_log, expected_metrics):
        """Общий процент повторов = 20.06% ± 1%"""
        exp = expected_metrics["rework_global"]
        actual = rework.compute_global_rework_pct(synthetic_log)
        assert actual == pytest.approx(exp["global_rework_pct"], rel=0.01)

    def test_rework_table_top_10(self, synthetic_log, expected_metrics):
        """Топ-10 операций по объёму с правильными rework_pct."""
        exp_top10 = expected_metrics["top10_operations_by_volume"]
        actual_df = rework.compute_rework_per_operation(synthetic_log)
        actual_top10 = actual_df.head(10).to_dict("records")
        
        for exp_row, act_row in zip(exp_top10, actual_top10):
            assert act_row["activity"] == exp_row["operation"]
            assert act_row["total"] == exp_row["total"]
            assert act_row["repeats"] == exp_row["repeats"]
            assert act_row["rework_pct"] == pytest.approx(exp_row["rework_pct"], abs=0.05)

    def test_duration_with_without_rework(self, synthetic_log, expected_metrics):
        """Средняя длительность с/без повторов."""
        exp = expected_metrics["case_duration"]
        actual = rework.compute_duration_comparison(synthetic_log)
        
        assert actual["n_cases_with_rework"] == exp["n_cases_with_rework"]
        assert actual["n_cases_without_rework"] == exp["n_cases_without_rework"]
        assert actual["avg_duration_with_rework_seconds"] == pytest.approx(
            exp["avg_with_rework_seconds"], rel=0.01
        )
        assert actual["avg_duration_without_rework_seconds"] == pytest.approx(
            exp["avg_without_rework_seconds"], rel=0.01
        )

    def test_process_metrics(self, synthetic_log, expected_metrics):
        """Вариативность путей и встречаемость операций."""
        exp = expected_metrics["process_metrics"]
        
        actual_variability = variants.compute_variability_pct(synthetic_log)
        actual_occurrence = variants.compute_mean_occurrence_pct(synthetic_log)
        actual_traces = variants.get_case_traces(synthetic_log).nunique()
        
        assert actual_traces == exp["unique_traces"]
        assert actual_variability == pytest.approx(exp["variability_pct"], abs=0.05)
        assert actual_occurrence == pytest.approx(exp["mean_occurrence_pct"], abs=0.05)

    def test_sojourn_top10(self, synthetic_log, expected_metrics):
        """Sojourn time для топ-10 операций."""
        exp = expected_metrics["sojourn_time_top10_operations"]
        df_sojourn = duration.compute_sojourn_time(synthetic_log)
        
        for op_name, exp_metrics in exp.items():
            op_data = df_sojourn[df_sojourn["activity"] == op_name]["sojourn_seconds"]
            assert op_data.mean() == pytest.approx(exp_metrics["avg_sec"], rel=0.02)
            assert op_data.median() == pytest.approx(exp_metrics["median_sec"], rel=0.02)
```

### Запуск golden tests

```cmd
cd backend
.venv\Scripts\pytest tests\golden -v --tb=short
```

Каждый тест выводит свою цифру и эталон в случае несовпадения, чтобы быстро локализовать проблему.

### Регенерация эталона

Если меняется логика расчёта намеренно (например, исправляем баг) — пересчитываем эталон:

```cmd
.venv\Scripts\python scripts\regenerate_golden_metrics.py
```

Скрипт читает `synthetic_log.xlsx`, вызывает все алгоритмы, перезаписывает `expected_metrics.json`. **Обязательно** review через `git diff` — каждое изменение цифр должно быть осознанным.

## Unit Tests — алгоритмы домена

### Принципы

1. **Чистые функции — простые тесты.** На вход — DataFrame, на выход — DataFrame/dict. Никакого мокинга БД.
2. **Минимальные фикстуры.** Делаем маленькие DataFrame'ы (5-10 строк) с известными значениями.
3. **Граничные случаи:** пустой DataFrame, один кейс, кейс с одной операцией, дубликаты, null значения.

### Пример

```python
# tests/unit/domain/mining/test_rework.py
import pandas as pd
import pytest
from datetime import datetime
from app.domain.mining import rework

def make_event(case_id, activity, t):
    return {
        "case_id": case_id,
        "activity": activity,
        "timestamp_start": t,
        "timestamp_end": t,
    }

class TestComputeReworkPerOperation:
    def test_no_repeats(self):
        df = pd.DataFrame([
            make_event("C1", "A", datetime(2025, 1, 1)),
            make_event("C1", "B", datetime(2025, 1, 2)),
            make_event("C2", "A", datetime(2025, 1, 3)),
        ])
        result = rework.compute_rework_per_operation(df)
        assert (result["repeats"] == 0).all()
        assert (result["rework_pct"] == 0).all()
    
    def test_one_repeat(self):
        df = pd.DataFrame([
            make_event("C1", "A", datetime(2025, 1, 1)),
            make_event("C1", "A", datetime(2025, 1, 2)),  # повтор
            make_event("C1", "B", datetime(2025, 1, 3)),
        ])
        result = rework.compute_rework_per_operation(df)
        row_a = result[result["activity"] == "A"].iloc[0]
        assert row_a["total"] == 2
        assert row_a["repeats"] == 1
        assert row_a["rework_pct"] == 50.0
    
    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["case_id", "activity", "timestamp_start", "timestamp_end"])
        result = rework.compute_rework_per_operation(df)
        assert len(result) == 0
    
    def test_repeats_only_within_case(self):
        """Повтор в C1 и C2 — это 2 повтора, не 1."""
        df = pd.DataFrame([
            make_event("C1", "A", datetime(2025, 1, 1)),
            make_event("C1", "A", datetime(2025, 1, 2)),
            make_event("C2", "A", datetime(2025, 1, 3)),
            make_event("C2", "A", datetime(2025, 1, 4)),
        ])
        result = rework.compute_rework_per_operation(df)
        row_a = result[result["activity"] == "A"].iloc[0]
        assert row_a["total"] == 4
        assert row_a["repeats"] == 2  # по 1 повтору в каждом кейсе
```

### Какие алгоритмы покрывать unit-тестами

Минимум — все функции из `02_DOMAIN_LOGIC.md`:

- `loading.load_event_log` — парсинг xlsx, маппинг колонок, типы данных, парсинг datetime.
- `loading.validate_event_log` — все проверки.
- `loading.deduplicate` — точные дубликаты.
- `health.health_check` — каждый из 5 чеков отдельно.
- `role_mapping.suggest_role_mapping` — авто-сопоставление по паттернам.
- `role_mapping.apply_role_mapping` — переименование activity, fallback на 'Не размечено'.
- `duration.compute_sojourn_time` — первое событие, последовательные события, между кейсами.
- `duration.compute_case_duration` — нормальные кейсы и пограничные (1 операция).
- `WorkdayCalculator.working_seconds` — выходные, праздники, частично в рабочее время.
- `rework.compute_rework_per_operation` — выше.
- `rework.split_cases_by_rework` — выше.
- `variants.get_case_traces` — порядок сортировки.
- `variants.get_top_n_variants` — равенство по n_cases.
- `variants.compute_variability_pct`, `compute_mean_occurrence_pct`.
- `graph.build_dfg` — узлы и рёбра.
- `graph.filter_dfg` — пороги.
- `sla.find_matching_rule` — приоритет правил (точное / wildcard).
- `sla.evaluate_operation_sla` — workdays vs calendar_days.
- `resources.compute_resource_workload`.
- `dynamics.compute_monthly_dynamics` — с фильтром и без.
- `filters.apply_filter` — каждый тип фильтра + комбинации.

## Integration Tests — API

### Test database

Для интеграционных тестов используется **отдельная БД** `process_mining_test`. Создаётся при первом запуске тестов, очищается между тестами через транзакции.

```python
# tests/integration/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.core.config import settings
from app.db.base import Base

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/process_mining", "/process_mining_test")

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(conn)
        yield session
        await session.close()
        await trans.rollback()  # откатываем все изменения теста

@pytest.fixture
async def client(db_session) -> AsyncClient:
    # Override db dependency to use db_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def admin_user(db_session):
    """Создаёт админа и возвращает с access-токеном."""
    ...

@pytest.fixture
async def analyst_user(db_session):
    ...
```

### Пример integration-теста

```python
# tests/integration/api/test_projects.py
import pytest

@pytest.mark.asyncio
async def test_create_project(client, analyst_user):
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "Description"},
        headers={"Authorization": f"Bearer {analyst_user.token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["created_by"]["id"] == analyst_user.id

@pytest.mark.asyncio
async def test_list_projects_returns_all(client, analyst_user, admin_user):
    """Все пользователи видят все проекты."""
    # Создаём 2 проекта разными пользователями
    await client.post("/api/v1/projects", json={"name": "P1"},
                      headers={"Authorization": f"Bearer {analyst_user.token}"})
    await client.post("/api/v1/projects", json={"name": "P2"},
                      headers={"Authorization": f"Bearer {admin_user.token}"})
    
    # Аналитик видит оба
    response = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {analyst_user.token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2

@pytest.mark.asyncio
async def test_delete_project_only_owner_or_admin(client, analyst_user, admin_user):
    # analyst_user создаёт
    r = await client.post("/api/v1/projects", json={"name": "P"},
                          headers={"Authorization": f"Bearer {analyst_user.token}"})
    project_id = r.json()["id"]
    
    # Другой analyst — отказ
    other_analyst = ...
    response = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {other_analyst.token}"},
    )
    assert response.status_code == 403
    
    # Admin может
    response = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {admin_user.token}"},
    )
    assert response.status_code == 204
```

### Что покрывать integration-тестами

Минимум для каждого ресурса:
- **CREATE:** успех, валидация полей, права.
- **READ:** список + детали, фильтры, права.
- **UPDATE:** успех, валидация, права.
- **DELETE:** успех, права, каскады (что блокирует удаление).

Особое внимание:
- Полный flow загрузки физического датасета (preview → upload → ready) с реальным мини-xlsx.
- Создание виртуального датасета и snapshot маппинга/SLA.
- Расчёт KPI после фоновой задачи.
- Дашборды с виджетами + получение данных виджета.

## E2E тесты (Playwright) — опционально

В MVP не обязательны. Если будут — покрыть:

1. Регистрация → логин → создание проекта → загрузка xlsx → просмотр дашборда (happy path).
2. Создание дашборда + добавление 3 виджетов.
3. Создание именованного среза + применение к дашборду.

## CI

В MVP — простой `make test` локально. Если будет CI (GitHub Actions / GitLab CI):

```yaml
# .github/workflows/test.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: cd backend && pip install -e ".[dev]"
      - run: cd backend && alembic upgrade head
      - run: cd backend && pytest tests/ -v
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm test && npm run lint
```

## Линтеры и типизация

### Backend

- **ruff** — формат + основная проверка (заменяет flake8 + isort + часть pylint).
- **mypy** — type checking в strict-режиме (`mypy --strict app/`).
- **pyproject.toml** содержит конфиг для обоих.

### Frontend

- **ESLint** + рекомендованные правила React + TypeScript.
- **Prettier** — форматирование.
- **TypeScript** в strict-режиме (`"strict": true` в tsconfig.json).

## Coverage

В MVP — не требование, но желательно:
- Backend domain layer: ≥ 90%.
- Backend services layer: ≥ 70%.
- Backend API layer: ≥ 60%.

Команда: `pytest --cov=app --cov-report=html`.

## Что читать дальше

- Последовательность работы → `07_ROADMAP.md`
- Конкретные задачи → `tasks/`
