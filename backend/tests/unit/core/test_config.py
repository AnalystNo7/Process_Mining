import pytest
from pydantic import ValidationError

from app.core.config import Settings

REQUIRED_ENV = {
    "APP_SECRET_KEY": "test_secret_key_at_least_32_characters_long",
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
    "CELERY_BROKER_URL": "redis://localhost:6379/1",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/2",
    "STORAGE_PATH": "/tmp/pm-storage",
    "BACKUP_PATH": "/tmp/pm-backups",
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Задаёт обязательные переменные окружения для Settings."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_settings_loads_from_env(env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)
    assert settings.DATABASE_URL == REQUIRED_ENV["DATABASE_URL"]
    assert settings.APP_SECRET_KEY == REQUIRED_ENV["APP_SECRET_KEY"]
    assert str(settings.STORAGE_PATH) == "/tmp/pm-storage"


def test_optional_fields_have_defaults(env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)
    assert settings.APP_ENV == "development"
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60
    assert settings.LDAP_ENABLED is False
    assert settings.DATABASE_POOL_SIZE == 10
    assert settings.LOG_LEVEL == "INFO"


def test_missing_required_field_raises(
    env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_origins_parsed_from_comma_separated(
    env: pytest.MonkeyPatch, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, http://localhost:3000")
    settings = Settings(_env_file=None)
    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://localhost:3000"]


def test_cors_origins_default_empty(env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)
    assert settings.CORS_ORIGINS == []
