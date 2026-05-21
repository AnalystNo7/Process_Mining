# 01. Модель данных и схема БД

## Обзор

Этот документ описывает все сущности системы, их связи, схему PostgreSQL и принципы работы с event log.

## Логическая модель (сущности)

```
                    ┌─────────┐
                    │  User   │
                    └────┬────┘
                         │ created_by
                         ▼
                    ┌─────────┐
                    │ Project │ (контейнер процесса)
                    └────┬────┘
                         │
        ┌────────────────┼──────────────────┬──────────────────┐
        ▼                ▼                  ▼                  ▼
┌───────────────┐ ┌─────────────┐  ┌──────────────┐  ┌────────────────┐
│ PhysicalDS    │ │ RoleMapping │  │   SLARule    │  │ AnnotationLayer│
│ (загр. xlsx)  │ │ (общий)     │  │  (правила)   │  │ (общие пометки)│
└───────┬───────┘ └─────────────┘  └──────────────┘  └────────────────┘
        │
        ▼
┌─────────────────┐
│   EventLog      │ (партиционированная таблица событий)
└─────────────────┘
        │
        ▼ ссылается
┌────────────────────┐
│  VirtualDataset    │ ← immutable снимок маппинга ролей + конфигурации
└────────┬───────────┘
         │
         ├──→ NamedSlice (именованный фильтр)
         ├──→ Dashboard (набор виджетов)
         │       └──→ DashboardWidget
         └──→ DatasetAnnotation (личные пометки)
```

## Схема PostgreSQL (DDL)

Ниже — полная схема БД. Все таблицы используют `BIGSERIAL` для PK, кроме `event_log` (`BIGINT` без serial — id генерируется при загрузке). Все timestamp хранятся как `TIMESTAMPTZ` (UTC).

### Схема `auth`

```sql
CREATE SCHEMA IF NOT EXISTS auth;

-- Пользователи
CREATE TABLE auth.users (
    id           BIGSERIAL PRIMARY KEY,
    username     VARCHAR(100) NOT NULL UNIQUE,
    email        VARCHAR(255) UNIQUE,
    full_name    VARCHAR(255),
    password_hash VARCHAR(255),  -- NULL для LDAP-пользователей
    is_ldap      BOOLEAN NOT NULL DEFAULT FALSE,
    role         VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'analyst')),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_username ON auth.users (username);
CREATE INDEX idx_users_active ON auth.users (is_active) WHERE is_active = TRUE;

-- Сессии (для refresh-токенов; access-токены JWT — stateless)
CREATE TABLE auth.refresh_tokens (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(255) NOT NULL UNIQUE,
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON auth.refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_expires ON auth.refresh_tokens (expires_at);

-- Audit log
CREATE TABLE auth.audit_log (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT REFERENCES auth.users(id) ON DELETE SET NULL,
    action       VARCHAR(100) NOT NULL,  -- e.g. 'project.create', 'dataset.upload', 'user.login'
    entity_type  VARCHAR(50),            -- e.g. 'project', 'physical_dataset'
    entity_id    BIGINT,
    metadata     JSONB,                  -- произвольные доп.данные
    ip_address   INET,
    user_agent   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON auth.audit_log (user_id, created_at DESC);
CREATE INDEX idx_audit_entity ON auth.audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_action ON auth.audit_log (action, created_at DESC);
```

### Схема `core` (метаданные)

```sql
CREATE SCHEMA IF NOT EXISTS core;

-- Проекты
CREATE TABLE core.projects (
    id           BIGSERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    created_by   BIGINT NOT NULL REFERENCES auth.users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted   BOOLEAN NOT NULL DEFAULT FALSE,  -- soft delete
    deleted_at   TIMESTAMPTZ
);

CREATE INDEX idx_projects_active ON core.projects (is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_projects_created_by ON core.projects (created_by);

-- Физические датасеты (загруженные xlsx, immutable)
CREATE TABLE core.physical_datasets (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_hash       VARCHAR(64) NOT NULL,  -- SHA-256
    storage_path    VARCHAR(500) NOT NULL, -- относительный путь в хранилище
    
    -- Маппинг колонок (применённый при загрузке)
    column_mapping  JSONB NOT NULL,
    -- Пример:
    -- {
    --   "case_id": "doc_id",
    --   "activity": "Операция",
    --   "timestamp_start": "in_progress_datetime",
    --   "timestamp_end": "completed_datetime",
    --   "resource": "task_user",
    --   "department": "task_user_department",
    --   "additional": {"doc_type": "doc_type", "doc_number": "doc_number"}
    -- }
    
    -- Статистика
    total_events    INTEGER NOT NULL,
    total_cases     INTEGER NOT NULL,
    unique_activities INTEGER NOT NULL,
    period_start    TIMESTAMPTZ,
    period_end      TIMESTAMPTZ,
    
    -- Health check
    health_status   VARCHAR(20) NOT NULL CHECK (health_status IN ('good', 'warning', 'poor')),
    health_report   JSONB NOT NULL,  -- см. 02_DOMAIN_LOGIC раздел Health Check
    
    -- Метаданные загрузки
    uploaded_by     BIGINT NOT NULL REFERENCES auth.users(id),
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          VARCHAR(20) NOT NULL DEFAULT 'ready'
                    CHECK (status IN ('uploading', 'validating', 'ready', 'failed')),
    error_message   TEXT
);

CREATE INDEX idx_physical_datasets_project ON core.physical_datasets (project_id);
CREATE INDEX idx_physical_datasets_status ON core.physical_datasets (status);

-- Маппинг подразделений → ролей (общий на проект)
CREATE TABLE core.role_mappings (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL DEFAULT 'Основной маппинг',
    version         INTEGER NOT NULL DEFAULT 1,  -- увеличивается при изменении
    
    -- Сам маппинг: подразделение → роль
    mapping         JSONB NOT NULL,
    -- Пример:
    -- {
    --   "Юридическое управление": "Юридическое управление",
    --   "Договорной отдел": "Договорной отдел",
    --   "Проект 001": "Инициатор",
    --   "Проект 002": "Инициатор",
    --   "Финансовое управление": "Финансовый блок",
    --   ...
    -- }
    
    -- Сами роли (для UI: чтобы знать, какие роли есть)
    roles           JSONB NOT NULL,
    -- Пример: ["Инициатор", "Юридическое управление", "Финансовый блок", ...]
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (project_id, version)
);

CREATE INDEX idx_role_mappings_project ON core.role_mappings (project_id, version DESC);

-- SLA-справочник (общий на проект)
CREATE TABLE core.sla_rules (
    id                BIGSERIAL PRIMARY KEY,
    project_id        BIGINT NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    role              VARCHAR(255) NOT NULL,
    operation_pattern VARCHAR(500) NOT NULL,  -- конкретное имя или '*'
    sla_value         NUMERIC(10, 2) NOT NULL,
    sla_unit          VARCHAR(20) NOT NULL CHECK (sla_unit IN ('workdays', 'calendar_days', 'workhours', 'hours')),
    tolerance_hours   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    target_compliance_pct NUMERIC(5, 2) NOT NULL DEFAULT 90.0,
    effective_from    DATE NOT NULL,
    effective_until   DATE,
    
    description       TEXT,
    created_by        BIGINT NOT NULL REFERENCES auth.users(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sla_rules_project ON core.sla_rules (project_id);
CREATE INDEX idx_sla_rules_role ON core.sla_rules (project_id, role);
CREATE INDEX idx_sla_rules_effective ON core.sla_rules (effective_from, effective_until);

-- Виртуальные датасеты (immutable снимок с применёнными правилами)
CREATE TABLE core.virtual_datasets (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          BIGINT NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    physical_dataset_id BIGINT NOT NULL REFERENCES core.physical_datasets(id),
    
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    
    -- Снимок маппинга ролей на момент создания (immutable)
    role_mapping_snapshot JSONB NOT NULL,
    -- {"mapping": {...}, "roles": [...], "version": 3}
    
    -- Снимок SLA-правил на момент создания (immutable)
    sla_rules_snapshot  JSONB NOT NULL,
    -- [{"id": 1, "role": "...", "operation_pattern": "...", "sla_value": 3, ...}, ...]
    -- Может быть пустым [] если SLA не настроены — тогда SLA-метрики недоступны.
    
    -- Конфигурация датасета (фильтры, применённые при создании)
    config              JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "filters": {
    --     "date_range": {"from": "2025-01-01", "to": "2025-10-31"},
    --     "doc_types": ["Договорный документ"],
    --     "exclude_test_cases": true
    --   }
    -- }
    
    -- Кэшированная статистика
    cached_stats        JSONB,
    -- {"total_cases": 1328, "total_events": 25606, "unique_activities": 507, ...}
    
    created_by          BIGINT NOT NULL REFERENCES auth.users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_personal         BOOLEAN NOT NULL DEFAULT TRUE  -- личный или общий
);

CREATE INDEX idx_virtual_datasets_project ON core.virtual_datasets (project_id);
CREATE INDEX idx_virtual_datasets_physical ON core.virtual_datasets (physical_dataset_id);
CREATE INDEX idx_virtual_datasets_owner ON core.virtual_datasets (created_by);

-- Именованные срезы (фильтры поверх виртуального датасета)
CREATE TABLE core.named_slices (
    id                  BIGSERIAL PRIMARY KEY,
    virtual_dataset_id  BIGINT NOT NULL REFERENCES core.virtual_datasets(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    
    filters             JSONB NOT NULL,
    -- Пример:
    -- {
    --   "departments": ["Юридическое управление"],
    --   "roles": ["Инициатор"],
    --   "date_range": {"from": "2025-07-01", "to": "2025-09-30"},
    --   "case_duration": {"min_days": 30},
    --   "with_rework": true,
    --   "resources": ["Иванов И.И."]
    -- }
    
    created_by          BIGINT NOT NULL REFERENCES auth.users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_named_slices_dataset ON core.named_slices (virtual_dataset_id);

-- Дашборды
CREATE TABLE core.dashboards (
    id                  BIGSERIAL PRIMARY KEY,
    virtual_dataset_id  BIGINT NOT NULL REFERENCES core.virtual_datasets(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    
    -- Глобальные фильтры дашборда (применяются ко всем виджетам по умолчанию)
    global_filters      JSONB NOT NULL DEFAULT '{}',
    
    -- Применённый именованный срез (опционально)
    applied_slice_id    BIGINT REFERENCES core.named_slices(id) ON DELETE SET NULL,
    
    -- Layout сетки виджетов (grid-positions, sizes)
    layout              JSONB NOT NULL DEFAULT '[]',
    
    created_by          BIGINT NOT NULL REFERENCES auth.users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dashboards_dataset ON core.dashboards (virtual_dataset_id);
CREATE INDEX idx_dashboards_owner ON core.dashboards (created_by);

-- Виджеты дашборда
CREATE TABLE core.dashboard_widgets (
    id                  BIGSERIAL PRIMARY KEY,
    dashboard_id        BIGINT NOT NULL REFERENCES core.dashboards(id) ON DELETE CASCADE,
    
    widget_type         VARCHAR(50) NOT NULL,
    -- Допустимые значения см. 04_UI.md раздел "Каталог виджетов"
    -- 'kpi_card', 'bar_chart', 'line_chart', 'heatmap', 'rework_table',
    -- 'sla_compliance_table', 'process_graph', 'top_paths_graph',
    -- 'resource_analysis_table', 'monthly_dynamics'
    
    title               VARCHAR(255) NOT NULL,
    
    -- Конфигурация виджета (зависит от widget_type)
    config              JSONB NOT NULL,
    -- Пример для kpi_card:
    -- {"metric": "total_cases", "format": "number", "icon": "FileTextOutlined"}
    -- Пример для bar_chart:
    -- {"x_axis": "month", "y_axis": "case_count", "group_by": "role"}
    
    -- Локальные фильтры виджета (опциональное переопределение global_filters)
    local_filters       JSONB,
    use_global_filters  BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Позиция в layout
    grid_x              INTEGER NOT NULL,
    grid_y              INTEGER NOT NULL,
    grid_width          INTEGER NOT NULL DEFAULT 4,
    grid_height         INTEGER NOT NULL DEFAULT 3,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_widgets_dashboard ON core.dashboard_widgets (dashboard_id);

-- Аннотации (визуальные пометки на дашбордах)
CREATE TABLE core.annotations (
    id                  BIGSERIAL PRIMARY KEY,
    virtual_dataset_id  BIGINT NOT NULL REFERENCES core.virtual_datasets(id) ON DELETE CASCADE,
    
    target_type         VARCHAR(30) NOT NULL
                        CHECK (target_type IN ('node', 'edge', 'case', 'time_range')),
    target_id           VARCHAR(500) NOT NULL,
    -- Для node: имя операции
    -- Для edge: "from_activity||to_activity"
    -- Для case: doc_id
    -- Для time_range: "2025-03-01|2025-04-30"
    
    text                TEXT NOT NULL,  -- произвольный текст пометки
    color               VARCHAR(20),    -- HEX-цвет для отображения
    
    created_by          BIGINT NOT NULL REFERENCES auth.users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_annotations_dataset ON core.annotations (virtual_dataset_id);
CREATE INDEX idx_annotations_target ON core.annotations (target_type, target_id);

-- Шаблоны загрузки (column_mapping) для проекта
CREATE TABLE core.upload_templates (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL DEFAULT 'Стандартный шаблон',
    column_mapping  JSONB NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_upload_templates_project ON core.upload_templates (project_id);

-- Глобальный справочник базовых ролей (для авто-разметки при создании проекта)
CREATE TABLE core.global_role_templates (
    id           BIGSERIAL PRIMARY KEY,
    role_name    VARCHAR(255) NOT NULL UNIQUE,
    patterns     JSONB NOT NULL,  -- список паттернов для авто-сопоставления
    -- Пример: ["Юридическое управление", "Юр.управление", "ЮУ"]
    sort_order   INTEGER NOT NULL DEFAULT 100,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by   BIGINT REFERENCES auth.users(id),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Схема `events` (event log)

Это самая большая таблица. Для MVP — простая таблица в PostgreSQL. Архитектурно — спрятана за интерфейсом `EventLogRepository`, чтобы при росте объёма можно было заменить на ClickHouse без переписывания бизнес-логики.

```sql
CREATE SCHEMA IF NOT EXISTS events;

CREATE TABLE events.event_log (
    id                  BIGSERIAL PRIMARY KEY,
    physical_dataset_id BIGINT NOT NULL REFERENCES core.physical_datasets(id) ON DELETE CASCADE,
    
    -- Стандартные поля process mining
    case_id             VARCHAR(255) NOT NULL,
    activity            VARCHAR(500) NOT NULL,
    timestamp_start     TIMESTAMPTZ NOT NULL,
    timestamp_end       TIMESTAMPTZ NOT NULL,
    resource            VARCHAR(255),       -- исполнитель (ФИО)
    department          VARCHAR(255),       -- подразделение исполнителя
    
    -- Доп. атрибуты (всё, что замапил аналитик в additional)
    attributes          JSONB,
    -- Пример:
    -- {
    --   "doc_type": "Договорный документ (ЕИ, МСЗ, Д/С, СОК)",
    --   "doc_number": "ЦПС-Д-25-7/5-16",
    --   "kr_state": "Зарегистрирован",
    --   "head_user_name": "Иванов И.И.",
    --   "route_type": "Согласование",
    --   "group_name": "Согласование цикл 1"
    -- }
    
    -- Денормализованное поле для быстрых запросов: длительность операции в секундах
    own_duration_sec    BIGINT GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (timestamp_end - timestamp_start))::BIGINT
    ) STORED
);

-- Индексы
CREATE INDEX idx_event_log_dataset ON events.event_log (physical_dataset_id);
CREATE INDEX idx_event_log_case ON events.event_log (physical_dataset_id, case_id);
CREATE INDEX idx_event_log_activity ON events.event_log (physical_dataset_id, activity);
CREATE INDEX idx_event_log_dept ON events.event_log (physical_dataset_id, department);
CREATE INDEX idx_event_log_resource ON events.event_log (physical_dataset_id, resource);
CREATE INDEX idx_event_log_time_start ON events.event_log (physical_dataset_id, timestamp_start);
CREATE INDEX idx_event_log_attrs_gin ON events.event_log USING GIN (attributes);

-- Композитный индекс для запросов по case_id с сортировкой по времени
CREATE INDEX idx_event_log_case_time ON events.event_log 
    (physical_dataset_id, case_id, timestamp_start);
```

### Партиционирование (на будущее, не в MVP)

В MVP таблица `event_log` обычная (без партиций), т.к. ожидаемые объёмы (до 500K строк) с этим легко работают. Если объём вырастет до миллионов, нужно партиционировать **по `physical_dataset_id`** (LIST partitioning) — это упростит удаление физических датасетов (DROP PARTITION вместо DELETE).

Для ClickHouse-варианта (будущая миграция) — партиционирование по `toYYYYMM(timestamp_start)` + `ORDER BY (physical_dataset_id, case_id, timestamp_start)`.

## Кэшированная статистика виртуального датасета

`virtual_datasets.cached_stats` — JSONB-объект с предрасчитанными метриками для быстрого отображения KPI. Пересчитывается при создании виртуального датасета (в фоновой задаче через Celery).

```json
{
  "total_cases": 1328,
  "total_events": 25606,
  "unique_activities": 507,
  "unique_resources": 257,
  "unique_departments": 118,
  "period_start": "2025-01-09T11:53:47Z",
  "period_end": "2025-11-07T16:19:56Z",
  "avg_case_duration_seconds": 1850000,
  "avg_case_duration_with_rework_seconds": 1905000,
  "avg_case_duration_without_rework_seconds": 1019000,
  "cases_with_rework": 1145,
  "cases_without_rework": 183,
  "global_rework_pct": 20.06,
  "unique_traces": 1194,
  "variability_pct": 89.9,
  "mean_occurrence_pct": 3.04,
  "computed_at": "2026-01-15T10:30:00Z"
}
```

## Жизненный цикл основных сущностей

### Физический датасет (immutable после загрузки)

1. **uploading** — файл принят, идёт сохранение в storage.
2. **validating** — парсинг xlsx, проверка маппинга, валидация типов.
3. **ready** — данные в `event_log`, доступны для использования.
4. **failed** — что-то пошло не так, см. `error_message`.

После `ready` файл **никогда не редактируется**. Если данные изменились — загружается новый физический датасет.

### Виртуальный датасет (immutable после создания)

1. Создаётся явно: указывается физ.датасет + берётся текущая версия маппинга ролей + текущие SLA + опциональные фильтры.
2. Сразу же делается snapshot — все справочники копируются в JSONB-поля.
3. Запускается фоновая задача расчёта `cached_stats`.
4. После этого виртуальный датасет **immutable** — любые изменения справочников не влияют на него.
5. Если нужно "обновить" — создаётся новый виртуальный датасет.

### Маппинг ролей (versioned)

Каждое обновление маппинга — это новая запись с инкрементом `version`. Старые версии хранятся для возможности reproduce. Виртуальные датасеты ссылаются на конкретную версию через snapshot.

### SLA-правила

Изменения SLA — это INSERT/UPDATE/DELETE записей. Виртуальные датасеты содержат snapshot, не пересчитываются. Для новых анализов с новым SLA — создавать новый виртуальный датасет.

### Дашборды и срезы (mutable)

Дашборды и срезы можно свободно редактировать — они оперируют над immutable виртуальным датасетом, поэтому не нарушают принцип воспроизводимости.

## Объёмные характеристики

Расчёт на типичный процесс на основе анализа Газпром ЦПС:

| Сущность | Размер записи | Ожидаемое кол-во | Объём в БД |
|----------|---------------|------------------|------------|
| event_log | ~500 байт | 500K строк × 5 процессов = 2.5M | ~1.5 ГБ |
| physical_datasets | ~2 КБ | ~50 (по 2-3 на проект × 20 проектов) | ~100 КБ |
| virtual_datasets | ~10 КБ (с snapshot) | ~200 (по 10 на проект) | ~2 МБ |
| dashboards | ~5 КБ | ~500 | ~2.5 МБ |
| dashboard_widgets | ~2 КБ | ~5000 | ~10 МБ |
| audit_log | ~500 байт | растёт ~1000/день × 365 = 365K/год | ~180 МБ/год |
| прочее | — | — | ~50 МБ |

**Итого через год эксплуатации:** ~2 ГБ. Backup pg_dump — ~500 МБ (сжатие).

## Принципы доступа к данным

Все запросы к `event_log` идут через интерфейс `EventLogRepository` (Python protocol):

```python
class EventLogRepository(Protocol):
    async def get_events_by_dataset(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> AsyncIterator[Event]: ...
    
    async def get_case_events(
        self, dataset_id: int, case_id: str
    ) -> list[Event]: ...
    
    async def count_events(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> int: ...
    
    async def get_unique_activities(self, dataset_id: int) -> list[str]: ...
    
    async def get_unique_departments(self, dataset_id: int) -> list[str]: ...
    
    async def aggregate_by_case(
        self, dataset_id: int, filters: EventFilter | None = None
    ) -> pd.DataFrame: ...
    
    # ... другие методы агрегации
```

Реализация для MVP — `PostgresEventLogRepository`, использует SQLAlchemy + asyncpg. На будущее: `ClickhouseEventLogRepository` — реализуется без изменений в бизнес-логике.

## Подход к работе с большими выборками

Для тяжёлых аналитических запросов (например, расчёт всех ping-pong метрик для виртуального датасета):

1. Не загружать всё в pandas одним SELECT. Использовать chunked reading (10K строк за раз) для больших датасетов.
2. Тяжёлые расчёты выполняются в фоновых задачах Celery, результат кэшируется в `virtual_datasets.cached_stats` или в отдельной таблице кэша метрик.
3. Для интерактивных запросов (фильтры дашборда) — оптимизировать SQL: использовать индексы, материализованные выборки, лимиты на возвращаемые объёмы.

## Что читать дальше

- Алгоритмы расчёта метрик → `02_DOMAIN_LOGIC.md`
- API для работы с этой моделью → `03_API.md`
- Тесты на корректность вычислений → `06_TESTING.md`
