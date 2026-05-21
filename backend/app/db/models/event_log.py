from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventLog(Base):
    """Журнал событий процесса. Самая крупная таблица.

    Спрятана за интерфейсом EventLogRepository (T10) — при росте объёма
    реализацию можно заменить на ClickHouse без изменения бизнес-логики.
    """

    __tablename__ = "event_log"
    __table_args__ = (
        Index("idx_event_log_dataset", "physical_dataset_id"),
        Index("idx_event_log_case", "physical_dataset_id", "case_id"),
        Index("idx_event_log_activity", "physical_dataset_id", "activity"),
        Index("idx_event_log_dept", "physical_dataset_id", "department"),
        Index("idx_event_log_resource", "physical_dataset_id", "resource"),
        Index("idx_event_log_time_start", "physical_dataset_id", "timestamp_start"),
        Index("idx_event_log_attrs_gin", "attributes", postgresql_using="gin"),
        Index("idx_event_log_case_time", "physical_dataset_id", "case_id", "timestamp_start"),
        {"schema": "events"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    physical_dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("core.physical_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[str] = mapped_column(String(255), nullable=False)
    activity: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timestamp_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Денормализованная длительность операции в секундах (generated column STORED).
    own_duration_sec: Mapped[int] = mapped_column(
        BigInteger,
        Computed(
            "EXTRACT(EPOCH FROM (timestamp_end - timestamp_start))::bigint",
            persisted=True,
        ),
    )
