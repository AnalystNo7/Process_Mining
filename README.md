# Process Mining

Инструмент Process Mining для анализа цифровых логов бизнес-процессов
систем электронного документооборота (TESSA) и ITSM. Главные аналитические задачи —
выявление узких мест (bottlenecks) и зацикленностей (rework) в процессах.

## Стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 15, Celery + Redis
- **Frontend:** TypeScript, React 18, Vite, Ant Design 5, Plotly.js, Cytoscape.js
- **Развёртывание:** нативно на Windows (без Docker)

## Требования к окружению

| Компонент  | Версия    |
|------------|-----------|
| Python     | 3.11.x    |
| Node.js    | 20.x LTS  |
| PostgreSQL | 15+       |
| Redis      | 7+        |

## Установка

```cmd
make install
```

Команда создаёт виртуальное окружение Python, ставит зависимости backend
(`pip install -e ".[dev]"`) и frontend (`npm install`).

На Linux/WSL используйте `make -f Makefile.linux install`.

## Конфигурация

Скопируйте `.env.example` в `backend/.env` и `frontend/.env`, заполните значения
(строка подключения к БД, секретный ключ JWT, пути хранилища).

## Запуск (development)

В трёх терминалах:

```cmd
make run-backend     # FastAPI на :8000
make run-celery      # Celery worker
make run-frontend    # Vite dev-сервер на :5173
```

Проверка backend: `GET http://localhost:8000/api/v1/health` → `{"status": "ok"}`.
Frontend: http://localhost:5173.

## Тесты и линтинг

```cmd
make test
make lint
```

## Резервное копирование

### Создание бэкапа

```cmd
make backup
```

Бэкап сохраняется в `backups/YYYY-MM-DD-HHMMSS/` и содержит:

- `db.dump` — дамп PostgreSQL в custom-формате (`pg_dump -Fc`);
- `uploads/` — копия каталога хранилища (загруженные xlsx-файлы);
- `manifest.json` — метаданные (версия системы, дата, размеры).

### Проверка целостности

```cmd
make verify-backup BACKUP_DIR=backups\2025-11-15-100000
```

### Восстановление

```cmd
make restore BACKUP_DIR=backups\2025-11-15-100000
```

**ВНИМАНИЕ:** восстановление сначала **удаляет** текущую БД и каталог хранилища,
затем восстанавливает данные из бэкапа. Перед восстановлением проверьте бэкап
командой `verify-backup`.

Параметры (`DB_HOST`, `DB_USER`, `DB_NAME`, `STORAGE_DIR`) переопределяются через
аргументы `make`, например `make backup STORAGE_DIR=D:\process-mining\storage`.
На Linux/WSL используйте `make -f Makefile.linux backup`.

### Рекомендации

- Делайте backup перед обновлением версии системы.
- Делайте backup еженедельно при активной работе.
- Храните последние 4 бэкапа, старые удаляйте вручную.

## Документация

Полное техническое задание — в каталоге [`docs/`](docs/):

- `00_OVERVIEW.md` — обзор проекта, цели, стек, глоссарий
- `01_DATA_MODEL.md` — модель данных и схема БД
- `02_DOMAIN_LOGIC.md` — алгоритмы process mining
- `03_API.md` — REST API контракт
- `04_UI.md` — описание экранов и виджетов
- `05_INFRA.md` — инфраструктура и развёртывание
- `06_TESTING.md` — стратегия тестирования
- `07_ROADMAP.md` — порядок выполнения задач
- `docs/tasks/` — 40 атомарных задач разработки (T01–T40)

Эталонные данные для regression-тестов — в [`golden_data/`](golden_data/).
