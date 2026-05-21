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
)
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Dashboard(Base):
    __tablename__ = "dashboards"
    __table_args__ = (
        Index("idx_dashboards_dataset", "virtual_dataset_id"),
        Index("idx_dashboards_owner", "created_by"),
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
    global_filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sql_text("'{}'::jsonb")
    )
    applied_slice_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("core.named_slices.id", ondelete="SET NULL")
    )
    layout: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=sql_text("'[]'::jsonb")
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        Index("idx_widgets_dashboard", "dashboard_id"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dashboard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.dashboards.id", ondelete="CASCADE"), nullable=False
    )
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    local_filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    use_global_filters: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sql_text("true")
    )
    grid_x: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_y: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_width: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("4"))
    grid_height: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sql_text("3")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Annotation(Base):
    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('node', 'edge', 'case', 'time_range')",
            name="ck_annotations_target_type",
        ),
        Index("idx_annotations_dataset", "virtual_dataset_id"),
        Index("idx_annotations_target", "target_type", "target_id"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    virtual_dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("core.virtual_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
