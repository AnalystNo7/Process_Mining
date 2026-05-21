from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Значения читаются из переменных окружения / .env
    (см. .env.example в корне репозитория)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Приложение
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str

    # База данных
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # LDAP (опционально)
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str | None = None
    LDAP_BIND_DN: str | None = None
    LDAP_BIND_PASSWORD: str | None = None
    LDAP_USER_SEARCH_BASE: str | None = None
    LDAP_USER_SEARCH_FILTER: str | None = None

    # Хранилище файлов
    STORAGE_PATH: Path
    MAX_UPLOAD_SIZE_MB: int = 200

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path | None = None
    LOG_ROTATION_SIZE_MB: int = 100
    LOG_ROTATION_BACKUPS: int = 10

    # Резервные копии
    BACKUP_PATH: Path

    # CORS. NoDecode отключает JSON-парсинг — значение приходит строкой
    # и разбирается валидатором _split_cors_origins.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    # Сервер
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """CORS_ORIGINS в .env задаётся строкой через запятую, не JSON-массивом."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
