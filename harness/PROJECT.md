# Карта проекта: CPS Process Mining

> Черновик. Пометки TODO — места, которые не удалось подтвердить по коду/докам.

## Что это

Корпоративный инструмент Process Mining для анализа цифровых логов
бизнес-процессов СЭД (TESSA) и ITSM. Главные аналитические задачи — выявление
узких мест (bottlenecks) и зацикленностей/повторов (rework). Пользователи —
аналитики: загружают лог (xlsx), строят виртуальные датасеты и дашборды
(граф процесса, длительности, SLA, повторы).

## Стек

**Backend** (`backend/pyproject.toml`):
- Python 3.11, FastAPI ≥0.115, Uvicorn
- SQLAlchemy 2.0 (async) + asyncpg, Alembic (16 миграций, head = 016)
- PostgreSQL 15+ (схемы `auth`, `core`, `events`), Redis 7+
- Celery ≥5.4 (broker/backend — Redis), pandas ≥2.2, openpyxl, pm4py ≥2.7,
  workalendar, structlog, python-jose (JWT), passlib, ldap3
- Линт/типы: ruff (line-length 100), mypy strict; тесты: pytest + pytest-asyncio

**Frontend** (`frontend/package.json`):
- TypeScript 5.5, React 18.3, Vite 5.3
- Ant Design 5.18 (+ @ant-design/icons), Plotly (plotly.js-dist-min 2.32 +
  react-plotly.js), Cytoscape 3.30 + cytoscape-dagre, react-grid-layout 1.5,
  bpmn-js 17.6
- @tanstack/react-query 5.40, zustand 4.5, react-router-dom 6.24, axios,
  react-hook-form + zod, dayjs
- Линт: eslint 8.57; тесты: vitest 1.6

**Развёртывание:** нативно на Windows, без Docker (README, `Makefile`);
для Linux/WSL — `Makefile.linux`. CI-конфигов в репозитории нет.

## Структура

```
backend/
  app/
    api/v1/          # HTTP-эндпоинты: auth, projects, physical/virtual_datasets,
                     # dashboards, analytics, role_mappings, sla, slices,
                     # annotations, users, global_roles, audit, tasks
    core/            # конфиг (Settings из env), security и пр.
    db/
      models/        # SQLAlchemy-модели по схемам: users(auth),
                     # projects/datasets/dashboards(core), event_log(events)
      repositories/  # доступ к данным
    domain/mining/   # чистая доменная логика на pandas (см. таблицу ниже)
    schemas/         # Pydantic-схемы запросов/ответов
    services/        # оркестрация: *_service.py (см. таблицу ниже)
    tasks/           # Celery: upload.py (загрузка xlsx), compute_stats.py (кэш метрик)
    scripts/         # create_admin
  alembic/versions/  # миграции 001–016 (в т.ч. дефолтные виджеты дашборда
                     # «Стандартный PM» и переименования их заголовков)
  tests/
    unit/            # доменка без БД
    integration/     # api + repositories; нужен живой PostgreSQL
    golden/          # regression на golden_data/synthetic_log.xlsx
frontend/
  src/
    api/             # axios-клиенты по ресурсам (client.ts — базовый)
    components/      # переиспользуемые (Plot, ProcessGraph — cytoscape)
    features/
      analytics/     # богатые вкладки: ProcessGraphTab, CasesTab, DatasetTab,
                     # StandardMetricsTab, FilterPanel
      dashboards/    # DashboardTabs (каркас вкладок), standardPmTabs (таксономия)
      widgets/       # WidgetCard/WidgetContent (рендер виджетов), AddWidgetModal,
                     # durationLayout (адаптивная высота), widgetMeta/widgetHints,
                     # OperationViewModeToggle (raw/role), OverviewFilterPanel
      datasets/, annotations/, auth/
    pages/           # роуты: Projects, ProjectDetail, VirtualDataset, Dashboard,
                     # AdminUsers, GlobalRoles, AuditLog, Me
    stores/          # zustand
    lib/             # утилиты (format.ts — formatDuration д/ч/м/с, table.ts, notify.ts)
docs/                # 00_OVERVIEW … 07_ROADMAP (+ diagrams, tasks)
golden_data/         # synthetic_log.xlsx + expected_metrics.json (эталон ±1%)
scripts/             # write_manifest.py, verify_backup.py (бэкапы)
harness/             # эта карта
```

## Ключевые модули и точки входа

| Модуль | Где | За что отвечает |
|--------|-----|-----------------|
| FastAPI app | `backend/app/main.py` | точка входа API (`/api/v1/...`, health) |
| Celery app | `backend/app/celery_app.py` | воркер фоновых задач |
| Доменка mining | `backend/app/domain/mining/` | `duration.py` (боксплот, CDF+SLA, теплокарта узких мест, work/wait), `graph.py` (DFG/process map), `rework.py`, `variants.py` (пути), `sla.py`+`workday.py`, `role_mapping.py` (dept→роль, `activity_with_role`, UNMAPPED_ROLE), `bpmn_export.py`, `loading.py`, `dynamics.py`, `resources.py`, `health.py`, `filters.py` |
| Данные виджетов | `backend/app/services/widget_data_service.py` | реестр `_HANDLERS` по `widget_type`; `compute_widget_data(db, widget, overrides)` — слияние временных query-override (limit/sort_by/stat/col_limit) и глобального `activity_level` из конфига VD |
| Шаблон дашборда | `backend/app/services/dashboard_service.py` | дефолтные виджеты «Стандартный PM» по вкладкам (`STANDARD_PM_TAB_KEYS`), CRUD дашбордов/виджетов |
| Аналитика | `backend/app/services/analytics_service.py` | загрузка DataFrame VD с фильтрами, `resolve_activity_level` (raw/role), `activity_column` |
| Кэш метрик | `backend/app/tasks/compute_stats.py` | `build_stats(df, activity_col)` → cached_stats VD |
| Роутер SPA | `frontend/src/router.tsx`, `main.tsx` | маршруты страниц |
| Дашборд | `frontend/src/pages/DashboardPage.tsx` → `features/dashboards/DashboardTabs.tsx` | вкладки/подвкладки (`standardPmTabs.ts`), GridLayout с виджетами, глобальные фильтры, переключатель raw/role |
| Виджеты | `frontend/src/features/widgets/WidgetCard.tsx` + `WidgetContent.tsx` | запрос данных (react-query, ключ включает overrides), контролы в шапке (топ-N, ранжирование, медиана/среднее, столбцы, SLA), рендер по типу |
| Граф процесса | `frontend/src/components/ProcessGraph.tsx`, `features/analytics/ProcessGraphTab.tsx` | cytoscape+dagre, зум/фуллскрин/PNG, панель путей, таблица операций |

## Как запустить / проверить

Windows (основная среда): `make install` → `make migrate` → `make create-admin`,
затем в трёх терминалах `make run-backend` (:8000), `make run-celery`,
`make run-frontend` (:5173). Health: `GET /api/v1/health` → `{"status":"ok"}`.
Linux/WSL: те же цели через `make -f Makefile.linux …`.

Конфиг: скопировать `.env.example` → `backend/.env` и `frontend/.env`
(DATABASE_URL, APP_SECRET_KEY, CELERY_*, STORAGE_PATH, BACKUP_PATH).

Проверки:
- Backend: `pytest tests/ -v` (unit — без БД; integration/golden — нужен
  PostgreSQL, тест-БД `process_mining_test` выводится из DATABASE_URL);
  `ruff check app/ tests/`, `mypy app/` (strict).
- Frontend: `npm run lint` (eslint), `npx tsc --noEmit`, `npm test` (vitest).
- Бэкапы: `make backup` / `make restore BACKUP_DIR=...` / `make verify-backup`.

## Known issues

1. **Протухшая схема тест-БД.** `tests/integration/conftest.py` создаёт таблицы
   через `Base.metadata.create_all` — существующие таблицы НЕ алтерятся. После
   добавления колонок в модели старая `process_mining_test` даёт
   `UndefinedColumnError` (наблюдалось с `dashboards.template_kind`, 66 упавших
   тестов). Лечение: в тест-БД `DROP SCHEMA auth, core, events CASCADE` и
   перезапуск тестов.
2. **Интеграционные и golden-тесты требуют живой PostgreSQL** — в облачных
   сессиях (без PG) прогоняются только unit + линтеры; интеграционные гоняет
   разработчик локально.
3. **Фронтенд почти не покрыт тестами** — единственный файл
   `features/widgets/durationLayout.test.ts`; `make test` для фронта зовёт
   vitest, который без watch-режима на пустом наборе может вести себя иначе —
   TODO: проверить поведение `npm test` в CI-подобном запуске.
4. **CI отсутствует** — линтеры/тесты запускаются вручную (`make lint`,
   `make test`).
5. TODO: содержание `docs/05_INFRA.md` (прод-развёртывание, AD/LDAP) и
   `docs/07_ROADMAP.md` в карту не сверено — уточнить при первом обращении
   к этим темам.
6. TODO: фактические версии Python/Node на прод-машине не видны из репозитория
   (README требует Python 3.11.x, Node 20.x LTS).
