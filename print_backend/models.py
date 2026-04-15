"""ORM models for users and print jobs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from print_backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    print_jobs: Mapped[list["PrintJob"]] = relationship("PrintJob", back_populates="user")


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    stl_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    preview_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    geometry_kind: Mapped[str] = mapped_column(String(32), nullable=False)  # wgsl-sdf | brep

    material: Mapped[str] = mapped_column(String(32), nullable=False)
    quality: Mapped[str] = mapped_column(String(32), nullable=False)
    infill: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    estimated_print_time_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    routing_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_speed: Mapped[str] = mapped_column(String(32), nullable=False)
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship("User", back_populates="print_jobs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stl_storage_key": self.stl_storage_key,
            "preview_image_url": self.preview_image_url,
            "geometry_kind": self.geometry_kind,
            "material": self.material,
            "quality": self.quality,
            "infill": self.infill,
            "color": self.color,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "notes": self.notes,
            "estimated_print_time_h": self.estimated_print_time_h,
            "estimated_cost": self.estimated_cost,
            "routing_hint": self.routing_hint,
            "customer_name": self.customer_name,
            "shipping_address": self.shipping_address,
            "delivery_speed": self.delivery_speed,
            "urgent": self.urgent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
