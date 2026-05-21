# T03: Конфигурация и логирование

## Цель
Pydantic-settings конфигурация (читает .env) + structlog для структурированных логов.

## Контекст
- `05_INFRA.md` разделы "Конфигурация (.env)" и "Логирование"

## DoD
- [ ] `app/core/config.py` с классом `Settings(BaseSettings)`, читающим все переменные из `.env.example`.
- [ ] `app/core/logging.py` настраивает structlog с JSON-форматом и ротацией файлов.
- [ ] `Settings` инстанцируется как singleton (`settings = Settings()`).
- [ ] При старте FastAPI вызывается `configure_logging(settings)`.
- [ ] Unit-тесты на парсинг .env.

## Реализация

`app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str
    
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str | None = None
    LDAP_BIND_DN: str | None = None
    LDAP_BIND_PASSWORD: str | None = None
    LDAP_USER_SEARCH_BASE: str | None = None
    LDAP_USER_SEARCH_FILTER: str | None = None
    
    STORAGE_PATH: Path
    MAX_UPLOAD_SIZE_MB: int = 200
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path | None = None
    LOG_ROTATION_SIZE_MB: int = 100
    LOG_ROTATION_BACKUPS: int = 10
    
    BACKUP_PATH: Path
    
    CORS_ORIGINS: list[str] = []
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

settings = Settings()
```

`app/core/logging.py` — реализация по примеру из `05_INFRA.md`.

В `app/main.py` добавить вызов `configure_logging(settings)` до создания FastAPI app.

## Тесты
- `test_settings_loads_from_env` — установить env vars, создать Settings(), проверить значения.
- `test_optional_fields_have_defaults`.
- `test_invalid_url_raises`.

## Acceptance
`python -c "from app.core.config import settings; print(settings.DATABASE_URL)"` показывает значение из .env. Логи пишутся в JSON в stdout и в файл.
