from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения.

    В рамках T02 содержит только параметры БД — необходимый минимум для
    SQLAlchemy-сессии и Alembic. Полный набор переменных (.env) добавляется
    в задаче T03.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_DEBUG: bool = True

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20


settings = Settings()
