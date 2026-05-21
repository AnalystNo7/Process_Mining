class AppError(Exception):
    """Базовая доменная ошибка приложения."""


class EntityNotFoundError(AppError):
    """Запрошенная сущность не найдена (HTTP 404)."""


class ConflictError(AppError):
    """Конфликт состояния — например, дублирование уникального поля (HTTP 409)."""


class BusinessRuleError(AppError):
    """Нарушение бизнес-правила (HTTP 422)."""


class PermissionDeniedError(AppError):
    """Недостаточно прав для операции (HTTP 403)."""
