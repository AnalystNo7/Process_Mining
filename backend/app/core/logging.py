import logging
import logging.handlers

import structlog

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Настраивает логирование: structlog в JSON-формате, вывод в stdout и
    опционально в файл с ротацией (см. 05_INFRA.md, раздел «Логирование»)."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if settings.LOG_FILE is not None:
        settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=settings.LOG_ROTATION_SIZE_MB * 1024 * 1024,
                backupCount=settings.LOG_ROTATION_BACKUPS,
                encoding="utf-8",
            )
        )

    logging.basicConfig(level=settings.LOG_LEVEL, handlers=handlers, force=True)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )
