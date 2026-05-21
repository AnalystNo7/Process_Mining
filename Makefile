# Makefile для Windows (нативная установка, без Docker).
# Для Linux/WSL используйте Makefile.linux: `make -f Makefile.linux <команда>`.

.PHONY: help install install-backend install-frontend migrate dev test lint format \
        backup restore create-admin clean build-frontend run-backend run-celery \
        run-frontend

help:
	@echo "Available commands:"
	@echo "  make install         - install all dependencies"
	@echo "  make migrate         - apply DB migrations"
	@echo "  make create-admin    - create first admin user (interactive)"
	@echo "  make dev             - run all services in dev mode (backend + frontend + celery)"
	@echo "  make test            - run all tests"
	@echo "  make lint            - run linters (ruff + mypy + eslint)"
	@echo "  make backup          - backup PostgreSQL database to .\backups\"
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
