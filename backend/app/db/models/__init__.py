"""ORM-модели. Импорт всех моделей здесь нужен для регистрации в Base.metadata
(используется Alembic env.py и тестами схемы)."""

from app.db.models.dashboards import Annotation, Dashboard, DashboardWidget
from app.db.models.datasets import NamedSlice, PhysicalDataset, VirtualDataset
from app.db.models.event_log import EventLog
from app.db.models.projects import (
    GlobalRoleTemplate,
    Project,
    RoleMapping,
    SLARule,
    UploadTemplate,
)
from app.db.models.users import AuditLog, RefreshToken, User

__all__ = [
    "Annotation",
    "AuditLog",
    "Dashboard",
    "DashboardWidget",
    "EventLog",
    "GlobalRoleTemplate",
    "NamedSlice",
    "PhysicalDataset",
    "Project",
    "RefreshToken",
    "RoleMapping",
    "SLARule",
    "UploadTemplate",
    "User",
    "VirtualDataset",
]
