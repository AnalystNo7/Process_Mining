from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PhysicalDataset(Base):
    __tablename__ = "physical_datasets"
    __table_args__ = (
        CheckConstraint(
            "health_status IN ('good', 'warning', 'poor')",
            name="ck_physical_datasets_health_status",
        ),
        CheckConstraint(
            "status IN ('uploading', 'validating', 'ready', 'failed')",
            name="ck_physical_datasets_status",
        ),
        Index("idx_physical_datasets_project", "project_id"),
        Index("idx_physical_datasets_status", "status"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    column_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_events: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_activities: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_status: Mapped[str] = mapped_column(String(20), nullable=False)
    health_report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="ready"
    )
    error_message: Mapped[str | None] = mapped_column(Text)


class VirtualDataset(Base):
    __tablename__ = "virtual_datasets"
    __table_args__ = (
        Index("idx_virtual_datasets_project", "project_id"),
        Index("idx_virtual_datasets_physical", "physical_dataset_id"),
        Index("idx_virtual_datasets_owner", "created_by"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    physical_dataset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.physical_datasets.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    role_mapping_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sla_rules_snapshot: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    cached_stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_personal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )


class NamedSlice(Base):
    __tablename__ = "named_slices"
    __table_args__ = (
        Index("idx_named_slices_dataset", "virtual_dataset_id"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    virtual_dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("core.virtual_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
