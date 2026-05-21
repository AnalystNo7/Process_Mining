# T01: Каркас репозитория

## Цель

Создать минимальный скелет проекта с двумя приложениями (backend + frontend) и инструментами разработки.

## Контекст для чтения

- `00_OVERVIEW.md` — раздел "Технологический стек", "Структура репозитория"
- `05_INFRA.md` — раздел "Структура проекта на диске", "Makefile"

## Definition of Done

- [ ] Создана структура папок согласно `00_OVERVIEW.md`.
- [ ] `backend/pyproject.toml` содержит зависимости: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic, pydantic-settings, python-jose, passlib, celery, redis, pandas, openpyxl, pm4py, workalendar, structlog. Dev: pytest, pytest-asyncio, httpx, ruff, mypy.
- [ ] `frontend/package.json` содержит зависимости: react@18, react-dom, react-router-dom@6, antd@5, @tanstack/react-query@5, zustand, axios, dayjs, plotly.js-dist-min, cytoscape, cytoscape-dagre, bpmn-js, @dnd-kit/core, @dnd-kit/sortable, react-hook-form, zod. Dev: typescript@5, vite, @vitejs/plugin-react, eslint, prettier.
- [ ] `Makefile` создан с командами из `05_INFRA.md`.
- [ ] `.env.example` создан со всеми переменными.
- [ ] `.gitignore` исключает `.venv/`, `node_modules/`, `.env`, `storage/`, `logs/`, `backups/`, `__pycache__/`, `*.pyc`, `dist/`, `.pytest_cache/`.
- [ ] `README.md` с инструкцией установки (5-10 строк) — копируйте из `05_INFRA.md`.
- [ ] FastAPI приложение запускается: `uvicorn app.main:app` отдаёт `{"status": "ok"}` на `GET /`.
- [ ] Vite-проект запускается: `npm run dev` показывает пустой роут с layout AntD (Sider+Header+Content).

## Шаги реализации

### Backend

1. Создать `backend/pyproject.toml` (PEP 621):

```toml
[project]
name = "process-mining-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "celery[redis]>=5.4.0",
    "redis>=5.0.0",
    "pandas>=2.2.0",
    "openpyxl>=3.1.0",
    "pm4py>=2.7.0",
    "workalendar>=17.0.0",
    "structlog>=24.1.0",
    "python-multipart>=0.0.9",
    "httpx>=0.27.0",  # для тестов и LDAP
    "ldap3>=2.9.0",   # для LDAP
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

2. Создать `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Process Mining API", version="0.1.0")

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
```

3. Создать пустые папки: `backend/app/{api,core,db,domain/{mining,repository},services,schemas}` с `__init__.py`.

4. Создать `backend/tests/{unit,integration,golden}/__init__.py`.

### Frontend

1. Создать `frontend/package.json`:

```json
{
  "name": "process-mining-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx}\"",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.24.0",
    "antd": "^5.18.0",
    "@ant-design/icons": "^5.3.0",
    "@tanstack/react-query": "^5.40.0",
    "zustand": "^4.5.0",
    "axios": "^1.7.0",
    "dayjs": "^1.11.10",
    "plotly.js-dist-min": "^2.32.0",
    "react-plotly.js": "^2.6.0",
    "cytoscape": "^3.30.0",
    "cytoscape-dagre": "^2.5.0",
    "bpmn-js": "^17.6.0",
    "@dnd-kit/core": "^6.1.0",
    "@dnd-kit/sortable": "^8.0.0",
    "react-hook-form": "^7.52.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@types/cytoscape": "^3.21.0",
    "@types/react-plotly.js": "^2.6.3",
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "vitest": "^1.6.0",
    "eslint": "^8.57.0",
    "@typescript-eslint/parser": "^7.13.0",
    "@typescript-eslint/eslint-plugin": "^7.13.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "prettier": "^3.3.0"
  }
}
```

2. Создать `vite.config.ts`, `tsconfig.json`, `index.html`.

3. Создать `src/main.tsx`, `src/App.tsx` с заглушкой layout AntD:

```tsx
// src/App.tsx
import { Layout, ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { BrowserRouter } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

export default function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Header>Process Mining</Header>
          <Layout>
            <Sider width={200}>Меню</Sider>
            <Content style={{ padding: 24 }}>Контент будет здесь</Content>
          </Layout>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}
```

### Корневые файлы

- `.env.example` — копировать из `05_INFRA.md`.
- `.gitignore` — стандартный (Python + Node + конкретные пути проекта).
- `Makefile` — копировать из `05_INFRA.md`.
- `README.md` — короткая инструкция: установка, запуск, ссылка на `docs/`.

## Тесты

- Запустить backend: `cd backend && python -m venv .venv && .venv\Scripts\pip install -e ".[dev]" && .venv\Scripts\uvicorn app.main:app` → должен отвечать на `GET /api/v1/health`.
- Запустить frontend: `cd frontend && npm install && npm run dev` → открыть http://localhost:5173, увидеть layout.

## Acceptance criteria

Если открывается http://localhost:5173 и виден AntD-layout, а `curl http://localhost:8000/api/v1/health` возвращает 200 — задача выполнена.
