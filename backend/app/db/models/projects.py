from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_active", "is_deleted", postgresql_where=text("is_deleted = false")),
        Index("idx_projects_created_by", "created_by"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RoleMapping(Base):
    __tablename__ = "role_mappings"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_role_mappings_project_version"),
        Index("idx_role_mappings_project", "project_id", text("version DESC")),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="Основной маппинг"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    roles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SLARule(Base):
    __tablename__ = "sla_rules"
    __table_args__ = (
        CheckConstraint(
            "sla_unit IN ('workdays', 'calendar_days', 'workhours', 'hours')",
            name="ck_sla_rules_unit",
        ),
        Index("idx_sla_rules_project", "project_id"),
        Index("idx_sla_rules_role", "project_id", "role"),
        Index("idx_sla_rules_effective", "effective_from", "effective_until"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    sla_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sla_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    tolerance_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0")
    )
    target_compliance_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default=text("90.0")
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UploadTemplate(Base):
    __tablename__ = "upload_templates"
    __table_args__ = (
        Index("idx_upload_templates_project", "project_id"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="Стандартный шаблон"
    )
    column_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Строка заголовков в исходном файле (0-based).
    header_row: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GlobalRoleTemplate(Base):
    __tablename__ = "global_role_templates"
    __table_args__ = ({"schema": "core"},)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    patterns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("100"))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
