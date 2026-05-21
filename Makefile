# Makefile для Windows (нативная установка, без Docker).
# Для Linux/WSL используйте Makefile.linux: `make -f Makefile.linux <команда>`.

.PHONY: help install install-backend install-frontend migrate dev test lint format \
        backup restore verify-backup create-admin clean build-frontend run-backend \
        run-celery run-frontend

help:
	@echo "Available commands:"
	@echo "  make install         - install all dependencies"
	@echo "  make migrate         - apply DB migrations"
	@echo "  make create-admin    - create first admin user (interactive)"
	@echo "  make dev             - run all services in dev mode (backend + frontend + celery)"
	@echo "  make test            - run all tests"
	@echo "  make lint            - run linters (ruff + mypy + eslint)"
	@echo "  make backup          - backup DB + uploads to .\backups\"
	@echo "  make restore BACKUP_DIR=...        - restore from a backup"
	@echo "  make verify-backup BACKUP_DIR=...  - check backup integrity"

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

# Параметры бэкапа. STORAGE_DIR — каталог хранилища (см. STORAGE_PATH в .env).
DB_HOST ?= localhost
DB_USER ?= pm_user
DB_NAME ?= process_mining
STORAGE_DIR ?= backend\storage
BACKUP_DIR ?= backups\$(shell powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd-HHmmss")

backup:
	@echo Creating backup in $(BACKUP_DIR)...
	@if not exist "$(BACKUP_DIR)\uploads" mkdir "$(BACKUP_DIR)\uploads"
	pg_dump -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME) -Fc -f "$(BACKUP_DIR)\db.dump"
	@if exist "$(STORAGE_DIR)" xcopy /E /I /Q /Y "$(STORAGE_DIR)" "$(BACKUP_DIR)\uploads" >nul
	@python scripts\write_manifest.py "$(BACKUP_DIR)"
	@echo Backup ready: $(BACKUP_DIR)

restore:
	@if not exist "$(BACKUP_DIR)\db.dump" (echo $(BACKUP_DIR)\db.dump not found - set BACKUP_DIR=path & exit /b 1)
	@echo WARNING: restore overwrites DB $(DB_NAME) and $(STORAGE_DIR)!
	@powershell -NoProfile -Command "if ((Read-Host 'Continue? [y/N]') -ne 'y') { exit 1 }"
	psql -h $(DB_HOST) -U $(DB_USER) -d postgres -c "DROP DATABASE IF EXISTS $(DB_NAME);"
	psql -h $(DB_HOST) -U $(DB_USER) -d postgres -c "CREATE DATABASE $(DB_NAME) OWNER $(DB_USER);"
	pg_restore -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME) "$(BACKUP_DIR)\db.dump"
	@if exist "$(STORAGE_DIR)" rmdir /s /q "$(STORAGE_DIR)"
	@xcopy /E /I /Q /Y "$(BACKUP_DIR)\uploads" "$(STORAGE_DIR)" >nul
	@echo Done.

verify-backup:
	@python scripts\verify_backup.py "$(BACKUP_DIR)"

build-frontend:
	cd frontend && npm run build

clean:
	cd backend && rmdir /s /q .venv
	cd frontend && rmdir /s /q node_modules
