# Карта проекта: CPS Process Mining

> Черновик. Пометки TODO — места, которые не удалось подтвердить по коду/докам.

## Что это

Инструмент Process Mining для анализа цифровых логов
бизнес-процессов СЭД (TESSA) и ITSM (Naumen). Главные аналитические задачи —
выявление узких мест (bottlenecks) и зацикленностей/повторов (rework).
Пользователи — аналитики (10–20 чел.): загружают лог (xlsx), строят виртуальные
датасеты и дашборды (граф процесса, длительности, SLA, повторы).

## Стек

**Backend** (`backend/pyproject.toml`, пакет process-mining-backend 0.1.0):
- Python ≥3.11, FastAPI ≥0.115, Uvicorn; ~9 100 строк
- SQLAlchemy 2.0 (async) + asyncpg, Alembic — 19 миграций, head = `019_sheet_name`
- PostgreSQL 15+ (схемы `auth`, `core`, `events`), Redis 7+
  (три БД: `/0` кэш, `/1` Celery broker, `/2` result backend)
- Celery ≥5.4, pandas ≥2.2, openpyxl, workalendar (произв. календарь РФ),
  structlog, python-jose (JWT), passlib, ldap3
- pm4py ≥2.7 объявлен, но НЕ используется — все алгоритмы написаны вручную
  на pandas (DFG, варианты, длительности и т.д.)
- Линт/типы: ruff (line-length 100), mypy strict (только `app/`);
  тесты: pytest + pytest-asyncio (`asyncio_mode=auto`); pytest-cov установлен,
  но покрытие не настроено

**Frontend** (`frontend/package.json`, 67 файлов в `src/`):
- TypeScript 5.5 (strict), React 18.3, Vite 5.3 — прокси в vite.config НЕТ,
  фронт ходит напрямую на `VITE_API_BASE_URL` (CORS на бэке)
- Ant Design 5.18 (+icons, locale ru_RU), Plotly (plotly.js-dist-min 2.32 +
  react-plotly.js), Cytoscape 3.30 + dagre, react-grid-layout 1.5
- @tanstack/react-query 5.40, zustand 4.5 (persist `pm-auth` в localStorage),
  react-router-dom 6.24, axios (JWT + refresh-очередь в `api/client.ts`), dayjs
- Объявлены, но не используются: @dnd-kit/*, react-hook-form, zod, bpmn-js
  (BPMN скачивается готовым файлом с бэка); `VITE_APP_NAME`/`VITE_LOG_LEVEL`
  объявлены, но не читаются
- Линт: eslint 8.57 (+react-hooks), prettier; тесты: vitest 1.6 (без конфига)

**Развёртывание:** нативно на Windows, Docker запрещён заказчиком
(`docs/05_INFRA.md`); prod — nssm-службы `ProcessMiningBackend`,
`ProcessMiningCelery`; Linux/WSL — `Makefile.linux`. CI нет.

## Структура

```
backend/
  app/
    main.py          # FastAPI app: CORS, 14 роутеров с prefix /api/v1, /health
    celery_app.py    # Celery «process_mining» (broker/backend Redis, TZ=UTC)
    api/v1/          # 14 роутеров: auth, users, projects, physical/virtual_datasets,
                     # role_mappings, sla, analytics (14 GET), dashboards,
                     # annotations, slices, tasks, audit, global_roles
    core/            # config.py (Settings; обязательные env без дефолтов:
                     # APP_SECRET_KEY, DATABASE_URL, CELERY_*, STORAGE_PATH,
                     # BACKUP_PATH), security (JWT), logging (structlog), exceptions
    db/
      models/        # 12 таблиц в 3 схемах: users/refresh_tokens/audit_log (auth),
                     # projects/role_mappings/sla_rules/upload_templates/
                     # global_role_templates/physical+virtual_datasets/case_paths/
                     # named_slices/dashboards/dashboard_widgets/annotations (core),
                     # event_log (events; generated own_duration_sec, GIN по attributes)
      repositories/  # PostgresEventLogRepository за Protocol (задел под ClickHouse)
    domain/mining/   # 13 модулей чистой доменки на pandas (см. таблицу)
    schemas/         # Pydantic-схемы, 1:1 с роутерами (15 файлов)
    services/        # 16 сервисов-оркестраторов (см. таблицу)
    tasks/           # Celery: upload.py (upload_dataset),
                     # compute_stats.py (compute_virtual_dataset_stats)
    scripts/         # create_admin (python -m app.scripts.create_admin)
  alembic/versions/  # 001–019: 001 схема, 002 сид ролей, 003–017 дефолтные
                     # виджеты/лэйауты, 009 case_paths, 018 header_row, 019 sheet_name
  tests/             # ~335 тестов в 43 файлах
    unit/            # 145: доменка (130) + core — без БД и env
    integration/     # 178: api (165) + repositories + cached_stats + migrations;
                     # нужен живой PostgreSQL
    golden/          # 12: regression на golden_data (без БД)
frontend/
  src/
    main.tsx         # вход: StrictMode>ErrorBoundary>ConfigProvider(ru)>QueryClient>Router
    router.tsx       # все маршруты (App.tsx нет); страницы через React.lazy
    api/             # 14 axios-модулей по ресурсам; client.ts — инстанс,
                     # Bearer-интерцептор, refresh-очередь на 401
    components/      # ProcessGraph (cytoscape+dagre), Plot, ErrorBoundary,
                     # ProtectedRoute (adminOnly), layout/ (AppLayout/Header/Sider)
    features/
      auth/          # LoginPage (логин/пароль + чекбокс LDAP)
      datasets/      # UploadWizard (3 шага: файл+лист+строка заголовка →
                     # маппинг колонок → поллинг обработки), Physical/VirtualDatasetsTab,
                     # RoleMappingTab (dept→роль, автоподбор), SlaRulesTab
      dashboards/    # DashboardTabs (вкладки Стандартные метрики/Обзор/Процесс/Детали,
                     # подвкладки process.*, details.*), standardPmTabs.ts
                     # (ключи синхронизированы с бэком STANDARD_PM_TAB_KEYS)
      widgets/       # WidgetContent (рендер 18 типов виджетов), WidgetCard,
                     # AddWidgetModal+widgetMeta (10 KPI-метрик), widgetHints,
                     # OverviewFilterPanel, OperationViewModeToggle (raw/role),
                     # durationLayout (адаптивная высота; единственный тест)
      analytics/     # ProcessGraphTab (граф+пути+таблица+BPMN), StandardMetricsTab,
                     # CasesTab, DatasetTab, FilterPanel
      annotations/   # AnnotationsTab
    pages/           # Projects, ProjectDetail, VirtualDataset, Dashboard, Me,
                     # AdminUsers, GlobalRoles, AuditLog, NotFound
    stores/          # authStore (zustand persist: токены, user, login/refresh/logout)
    lib/             # format.ts (даты/длительности), notify.ts, table.ts
    styles/          # tokens.css, shell.css, components.css, antd-overrides.css
docs/                # ТЗ: 00_OVERVIEW … 07_ROADMAP + tasks/T01–T40 + diagrams
golden_data/         # synthetic_log.xlsx (~2.5 МБ, обезличенный лог TESSA) +
                     # expected_metrics.json (1328 кейсов, 25 606 событий, допуск ±1%)
scripts/             # write_manifest.py, verify_backup.py (бэкапы)
harness/             # карта (этот файл), журналы DECISIONS.md/LESSONS.md,
                     # REQUIREMENTS.md (реестр требований, 81 карточка),
                     # templates/ (BRIEF, PLAN, REQUIREMENTS — шаблоны)
tasks/               # артефакты цикла задач (BRIEF/PLAN по задачам)
```

## Ключевые модули и точки входа

| Модуль | Где | За что отвечает |
|--------|-----|-----------------|
| FastAPI app | `backend/app/main.py` | точка входа API (`/api/v1/...`, health) |
| Celery app | `backend/app/celery_app.py` | воркер: upload_dataset, compute_virtual_dataset_stats |
| Доменка mining | `backend/app/domain/mining/` | `duration.py` (own/sojourn, боксплот, CDF, теплокарта узких мест, work/wait), `graph.py` (DFG + `__start__`/`__end__`, filter/limit), `variants.py` (path_hash sha1, топ-пути, coverage), `rework.py`, `sla.py` (приоритет правил role+op > role+* > *+op > *+*) + `workday.py` (workalendar РФ, окно 09–18 МСК), `role_mapping.py` (dept→роль, UNMAPPED), `bpmn_export.py` (DFG→BPMN XML, не Inductive Miner), `loading.py` (xlsx→DataFrame, МСК→UTC, валидация, дедуп), `dynamics.py` (гранулярность D/W/M/Q/Y, бакетизация в МСК), `resources.py`, `health.py` (good/warning/poor), `filters.py` (EventFilter) |
| Данные виджетов | `backend/app/services/widget_data_service.py` | реестр `_HANDLERS` по `widget_type` (18 типов); `compute_widget_data` — слияние query-override (limit/sort_by/stat/col_limit/granularity) и глобального `activity_level` VD |
| Шаблон дашборда | `backend/app/services/dashboard_service.py` | дефолтные виджеты «Стандартный PM» по вкладкам (`STANDARD_PM_TAB_KEYS`), CRUD дашбордов/виджетов |
| Аналитика | `backend/app/services/analytics_service.py` | загрузка DataFrame VD с фильтрами, `resolve_activity_level` (raw/role), `activity_column` |
| Кэш метрик | `backend/app/tasks/compute_stats.py` | `build_stats(df, activity_col)` → cached_stats VD + кэш case_paths |
| Хранение событий | `backend/app/db/repositories/event_log.py` | `PostgresEventLogRepository` за Protocol `EventLogRepository` |
| Роутер SPA | `frontend/src/router.tsx`, `main.tsx` | маршруты страниц, ProtectedRoute/adminOnly |
| API-клиент | `frontend/src/api/client.ts` | axios, Bearer из authStore, refresh-очередь на 401, тосты ошибок |
| Дашборд | `frontend/src/pages/DashboardPage.tsx` → `features/dashboards/DashboardTabs.tsx` | вкладки/подвкладки, GridLayout, глобальные фильтры, raw/role |
| Виджеты | `frontend/src/features/widgets/WidgetCard.tsx` + `WidgetContent.tsx` | запрос данных (react-query, ключ с overrides), контролы в шапке (топ-N, ранжирование, медиана/среднее, гранулярность, SLA), рендер по типу |
| Граф процесса | `frontend/src/components/ProcessGraph.tsx`, `features/analytics/ProcessGraphTab.tsx` | cytoscape+dagre, зум/фуллскрин/PNG, панель путей, таблица операций |

## Как запустить / проверить

Windows (основная среда): `make install` → `make migrate` → `make create-admin`,
затем в трёх терминалах `make run-backend` (:8000), `make run-celery`
(`--pool=solo`), `make run-frontend` (:5173). Health: `GET /api/v1/health` →
`{"status":"ok"}`. Linux/WSL: те же цели через `make -f Makefile.linux …`.

Конфиг: `.env.example` → `backend/.env` и `frontend/.env`. Обязательные без
дефолтов: `APP_SECRET_KEY`, `DATABASE_URL`, `CELERY_BROKER_URL`,
`CELERY_RESULT_BACKEND`, `STORAGE_PATH`, `BACKUP_PATH`.

Проверки:
- Backend: `pytest tests/ -v` (unit и golden — без БД; integration — нужен
  PostgreSQL; тест-БД = замена `/process_mining` → `/process_mining_test`
  в DATABASE_URL; схема создаётся `Base.metadata.create_all`, Celery `.delay`
  замокан); `ruff check app/ tests/`, `mypy app/` (strict).
- Frontend: `npm run lint`, `npx tsc --noEmit`, `npm test` (vitest).
- Всё разом: `make test`, `make lint`, `make format`.
- Бэкапы: `make backup` (pg_dump -Fc + uploads + manifest.json) /
  `make restore BACKUP_DIR=...` (сначала ДРОПАЕТ БД!) / `make verify-backup`.

## Known issues

1. **Протухшая схема тест-БД.** `tests/integration/conftest.py` создаёт таблицы
   через `Base.metadata.create_all` — существующие таблицы НЕ алтерятся. После
   добавления колонок в модели старая `process_mining_test` даёт
   `UndefinedColumnError` (наблюдалось с `dashboards.template_kind`, 66 упавших
   тестов). Лечение: в тест-БД `DROP SCHEMA auth, core, events CASCADE` и
   перезапуск тестов.
2. **Интеграционные тесты требуют живой PostgreSQL** — в облачных сессиях
   (без PG) прогоняются unit + golden + линтеры; интеграционные гоняет
   разработчик локально.
3. **Фронтенд почти не покрыт тестами** — единственный файл
   `features/widgets/durationLayout.test.ts` (5 тестов, чистая логика);
   vitest без собственного конфига, jsdom/testing-library не подключены.
4. **CI отсутствует** — линтеры/тесты запускаются вручную (`make lint`,
   `make test`); pytest-cov установлен, но покрытие нигде не настроено.
5. **Мёртвые зависимости.** Backend: pm4py объявлен, не импортируется.
   Frontend: @dnd-kit/*, react-hook-form, zod, bpmn-js не используются;
   `VITE_APP_NAME`/`VITE_LOG_LEVEL` не читаются. Задел или остатки — TODO
   уточнить у владельца перед удалением.
6. TODO: фактические версии Python/Node на прод-машине не видны из репозитория
   (README требует Python 3.11.x, Node 20.x LTS).
7. TODO: как фронт раздаётся в prod — `docs/05_INFRA.md` упоминает раздачу
   статики через FastAPI и опциональный reverse proxy, в `app/main.py`
   раздача статики не подтверждена.
8. TODO: генератор `golden_data/expected_metrics.json` в репозитории
   отсутствует (docs/06_TESTING: «уже сгенерирован»).
