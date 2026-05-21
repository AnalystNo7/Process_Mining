# 05. Инфраструктура и развёртывание

## Целевая среда

**Development:** Windows 10/11 машина разработчика, нативная установка (без Docker).

**Production-like (на той же машине или сервере):** аналогично нативная установка. Опционально — Linux-сервер. Docker не используется по требованию заказчика.

## Требования к окружению

| Компонент   | Версия       | Назначение                              |
|-------------|--------------|------------------------------------------|
| Python      | 3.11.x       | Backend                                  |
| Node.js     | 20.x LTS     | Frontend (сборка + dev-сервер)           |
| PostgreSQL  | 15+          | Основная БД                              |
| Redis       | 7+           | Брокер Celery + кэш                      |
| Git         | 2.40+        | Контроль версий                          |
| Make        | 4.x          | Запуск команд (на Windows — GnuWin32 или WSL) |

**Дополнительно для production-like на Windows:**
- nssm (Non-Sucking Service Manager) — для запуска FastAPI/Celery как Windows Service.

## Установка зависимостей на Windows

Описание для README, чтобы разработчик мог поднять окружение с нуля.

### 1. Установка Python 3.11

Скачать с https://www.python.org/downloads/release/python-3119/, при установке отметить "Add Python to PATH".

Проверка: `python --version` → `Python 3.11.9`.

### 2. Установка Node.js 20 LTS

Скачать с https://nodejs.org/en/download — пакет LTS (20.x).

Проверка: `node -v` → `v20.x.x`, `npm -v` → `10.x.x`.

### 3. Установка PostgreSQL 15+

Скачать с https://www.postgresql.org/download/windows/ — EDB-инсталлер. При установке:
- Запомнить пароль `postgres`-пользователя.
- Установить порт 5432 (стандартный).
- Включить компоненты pgAdmin (опционально, удобно).

После установки создать БД для проекта:

```sql
CREATE DATABASE process_mining;
CREATE USER pm_user WITH PASSWORD 'pm_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE process_mining TO pm_user;
```

### 4. Установка Redis

Самый простой путь на Windows — **Memurai** (Redis-совместимый сервер для Windows): https://www.memurai.com/get-memurai

Альтернатива — Redis через WSL2 или Redis для Windows (неофициальный порт, до 5.x). Memurai — production-ready, рекомендуется.

### 5. Установка Make (опционально)

Скачать GnuWin32 Make: http://gnuwin32.sourceforge.net/packages/make.htm — или установить через `winget install GnuWin32.Make`.

Альтернатива — использовать команды напрямую без Make (см. ниже).

## Структура проекта на диске

```
C:\dev\process-mining\
├── backend\
│   ├── app\
│   ├── alembic\
│   ├── tests\
│   ├── pyproject.toml
│   ├── .venv\                  ← Python virtual env (gitignore)
│   └── .env                    ← локальная конфигурация (gitignore)
├── frontend\
│   ├── src\
│   ├── public\
│   ├── package.json
│   ├── node_modules\           ← npm packages (gitignore)
│   └── .env                    ← локальная конфигурация frontend (gitignore)
├── golden_data\
│   ├── synthetic_log.xlsx
│   └── expected_metrics.json
├── docs\                       ← данные ТЗ
├── scripts\
├── storage\                    ← локальное хранилище xlsx-файлов (gitignore)
├── logs\                       ← логи приложения (gitignore)
├── backups\                    ← дампы БД (gitignore)
├── Makefile
├── .env.example
└── README.md
```

## Конфигурация (`.env`)

**Файл `.env.example`** (коммитится в репозиторий):

```bash
# === Backend ===
APP_ENV=development              # development | production
APP_DEBUG=true
APP_SECRET_KEY=change_me_to_random_string_min_32_chars

# Database
DATABASE_URL=postgresql+asyncpg://pm_user:pm_password_change_me@localhost:5432/process_mining
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# LDAP (опционально)
LDAP_ENABLED=false
LDAP_SERVER=ldap://ldap.example.com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_SEARCH_FILTER=(sAMAccountName={username})

# Storage
STORAGE_PATH=C:\dev\process-mining\storage
MAX_UPLOAD_SIZE_MB=200

# Logging
LOG_LEVEL=INFO
LOG_FILE=C:\dev\process-mining\logs\backend.log
LOG_ROTATION_SIZE_MB=100
LOG_ROTATION_BACKUPS=10

# Backup
BACKUP_PATH=C:\dev\process-mining\backups

# CORS (для dev)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Server
API_HOST=0.0.0.0
API_PORT=8000

# === Frontend ===
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=Process Mining
VITE_LOG_LEVEL=warn
```

**Важно:** `.env` всегда в `.gitignore`. `.env.example` — в репозитории.

## Makefile

```makefile
.PHONY: help install install-backend install-frontend migrate dev test lint format \
        backup restore create-admin clean build-frontend run-backend run-celery \
        run-frontend run-all

help:
	@echo "Available commands:"
	@echo "  make install         - install all dependencies"
	@echo "  make migrate         - apply DB migrations"
	@echo "  make create-admin    - create first admin user (interactive)"
	@echo "  make dev             - run all services in dev mode (backend + frontend + celery)"
	@echo "  make test            - run all tests"
	@echo "  make lint            - run linters (ruff + mypy + eslint)"
	@echo "  make backup          - backup PostgreSQL database to ./backups/"
	@echo "  make restore         - restore from latest backup"

install: install-backend install-frontend

install-backend:
	cd backend && python -m venv .venv
	cd backend && .venv\Scripts\pip install --upgrade pip
	cd backend && .venv\Scripts\pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

migrate:
	cd backend && .venv\Scripts\alembic upgrade head

create-admin:
	cd backend && .venv\Scripts\python -m app.scripts.create_admin

run-backend:
	cd backend && .venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-celery:
	cd backend && .venv\Scripts\celery -A app.celery_app worker --loglevel=info --pool=solo

run-frontend:
	cd frontend && npm run dev

dev:
	@echo "Запустите три терминала параллельно:"
	@echo "  Терминал 1: make run-backend"
	@echo "  Терминал 2: make run-celery"
	@echo "  Терминал 3: make run-frontend"

test:
	cd backend && .venv\Scripts\pytest tests\ -v
	cd frontend && npm test

lint:
	cd backend && .venv\Scripts\ruff check app\ tests\
	cd backend && .venv\Scripts\mypy app\
	cd frontend && npm run lint

format:
	cd backend && .venv\Scripts\ruff format app\ tests\
	cd frontend && npm run format

backup:
	@if not exist backups mkdir backups
	pg_dump -U pm_user -h localhost -F c -b -v -f "backups\process_mining_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%.dump" process_mining

restore:
	@echo "Usage: pg_restore -U pm_user -h localhost -d process_mining -c -v backups\<filename>.dump"

build-frontend:
	cd frontend && npm run build

clean:
	cd backend && rmdir /s /q .venv
	cd frontend && rmdir /s /q node_modules
```

**Примечание для Windows:** в Makefile используются Windows-пути (`\` и `\Scripts\`). Если разрабатываете в WSL/Linux — нужна Linux-версия (см. ниже Linux-Makefile в репозитории).

## Запуск в режиме разработки

Три терминала:

**Терминал 1 — Backend (FastAPI):**
```cmd
cd C:\dev\process-mining\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Терминал 2 — Celery worker:**
```cmd
cd C:\dev\process-mining\backend
.venv\Scripts\activate
celery -A app.celery_app worker --loglevel=info --pool=solo
```

**Важно:** на Windows для Celery нужно `--pool=solo` или `--pool=threads`. Стандартный `prefork` не работает.

**Терминал 3 — Frontend (Vite dev server):**
```cmd
cd C:\dev\process-mining\frontend
npm run dev
```

Открыть в браузере: http://localhost:5173.

## Production-like запуск на Windows

Для долгого работающего экземпляра — через **Windows Services** с помощью nssm.

### 1. Сборка frontend

```cmd
cd C:\dev\process-mining\frontend
npm run build
```

Получаем `frontend\dist\` со статикой.

### 2. Настройка FastAPI на раздачу статики

В `app/main.py` добавить:

```python
if settings.APP_ENV == "production":
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
```

### 3. Запуск через gunicorn (Linux) или uvicorn (Windows)

На Windows используем uvicorn без gunicorn (gunicorn не поддерживает Windows). Параметры production:

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-access-log
```

### 4. Установка как Windows Service через nssm

```cmd
nssm install ProcessMiningBackend "C:\dev\process-mining\backend\.venv\Scripts\python.exe" "-m" "uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "8000" "--workers" "4"
nssm set ProcessMiningBackend AppDirectory C:\dev\process-mining\backend
nssm set ProcessMiningBackend AppStdout C:\dev\process-mining\logs\backend-service.log
nssm set ProcessMiningBackend AppStderr C:\dev\process-mining\logs\backend-service.err
nssm start ProcessMiningBackend
```

Аналогично для Celery:

```cmd
nssm install ProcessMiningCelery "C:\dev\process-mining\backend\.venv\Scripts\celery.exe" "-A" "app.celery_app" "worker" "--loglevel=info" "--pool=solo"
nssm set ProcessMiningCelery AppDirectory C:\dev\process-mining\backend
nssm start ProcessMiningCelery
```

### 5. Reverse proxy (опционально)

Если нужен HTTPS или nice URL — поставить **IIS** с URL Rewrite или **nginx for Windows** перед uvicorn.

## Backup и восстановление

### Бэкап

`make backup` — выполняет `pg_dump` в `backups\process_mining_YYYYMMDD_HHMM.dump`.

Файлы xlsx в `storage\` копируются вручную (rsync/robocopy).

### Восстановление

```cmd
make restore
# показывает инструкцию:
pg_restore -U pm_user -h localhost -d process_mining -c -v backups\<filename>.dump
```

### Ротация бэкапов

Раз в неделю удалять старые бэкапы вручную или скриптом:

```powershell
Get-ChildItem .\backups\*.dump | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item
```

## Логирование

### Backend

Используется **structlog** с JSON-форматом. Все логи пишутся:
- В **stdout** (для dev и Docker-сред).
- В **файл** `logs/backend.log` (для production).

Ротация — встроенная в logging через `RotatingFileHandler` (100 МБ, 10 бэкапов).

Конфигурация в `app/core/logging.py`:

```python
import structlog
import logging.handlers

def configure_logging(settings):
    handlers = [logging.StreamHandler()]
    if settings.LOG_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_ROTATION_SIZE_MB * 1024 * 1024,
            backupCount=settings.LOG_ROTATION_BACKUPS,
            encoding='utf-8',
        )
        handlers.append(file_handler)
    
    logging.basicConfig(level=settings.LOG_LEVEL, handlers=handlers)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )
```

### Frontend

В dev — обычный `console.log`. В production — отправка ошибок в backend через специальный эндпоинт `POST /api/v1/client-errors` (опционально, на будущее).

## Миграции БД

**Alembic** — стандарт для SQLAlchemy. Структура:

```
backend\alembic\
├── alembic.ini
├── env.py
├── script.py.mako
└── versions\
    ├── 001_initial_schema.py
    ├── 002_add_health_report_jsonb.py
    └── ...
```

Команды:
- `alembic revision --autogenerate -m "description"` — создать миграцию из изменений моделей.
- `alembic upgrade head` — применить все миграции.
- `alembic downgrade -1` — откатить последнюю.

В Makefile: `make migrate` = `alembic upgrade head`.

**Важно:** все миграции должны быть **обратимыми** (есть `downgrade()`).

## Storage файлов

Загруженные xlsx-файлы хранятся локально в `STORAGE_PATH`:

```
storage\
├── projects\
│   ├── 1\                              ← project_id=1
│   │   ├── physical_42_2025-11-15_<hash>.xlsx
│   │   └── physical_43_2025-11-20_<hash>.xlsx
│   ├── 2\
│   └── ...
└── tmp\                                ← временные превью-файлы (TTL 1 час)
    └── tmp_abc123.xlsx
```

Каждый файл идентифицируется уникальным путём, сохраняется его SHA-256-хэш в БД для контроля целостности.

**Очистка временных файлов** — фоновая задача Celery beat (раз в час).

## CORS

В dev: разрешён `http://localhost:5173` (Vite dev-server).

В production: `CORS_ORIGINS` пуст (frontend отдаётся с того же origin) — CORS не нужен.

## Безопасность

1. **JWT-токены** подписываются `APP_SECRET_KEY` (>= 32 символа).
2. **Пароли** хранятся как bcrypt-хэши (через `passlib`).
3. **HTTPS** — на уровне reverse proxy (nginx/IIS), не в самом приложении.
4. **SQL-инъекции** — невозможны при использовании SQLAlchemy ORM с параметризованными запросами.
5. **CSRF** — не нужен для JWT auth (нет cookies). Если переходим на cookie-auth — добавлять CSRF-токены.
6. **Rate limiting** — на будущее (slowapi или nginx-rate-limit). В MVP — не требуется (10-20 пользователей).
7. **Файлы** — валидация типа (только xlsx/xls), максимальный размер 200 МБ, проверка SHA-256.
8. **Audit log** пишется на все мутирующие операции (см. `01_DATA_MODEL.md` раздел `auth.audit_log`).

## Мониторинг

В MVP не предусмотрен сложный мониторинг. Минимум:
- Эндпоинт `GET /health` для liveness/readiness.
- Логи в файлах.
- Audit log в БД.

На будущее: Prometheus metrics endpoint, Sentry для error tracking.

## Что читать дальше

- Тестирование → `06_TESTING.md`
- Порядок разработки → `07_ROADMAP.md`
- Атомарные задачи → `tasks/`
