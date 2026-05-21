# Process Mining — Backend

FastAPI-приложение для анализа цифровых логов бизнес-процессов.

## Требования

- Python 3.11.x
- PostgreSQL 15+
- Redis 7+ (брокер Celery)

## Установка

```cmd
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -e ".[dev]"
```

На Linux/WSL — `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`.

## Запуск (development)

```cmd
.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: `GET http://localhost:8000/api/v1/health` → `{"status": "ok"}`.

## Тесты

```cmd
.venv\Scripts\pytest tests\ -v
```

## Линтинг

```cmd
.venv\Scripts\ruff check app\ tests\
.venv\Scripts\mypy app\
```

Структура и архитектура описаны в `../docs/` (см. `00_OVERVIEW.md`).
