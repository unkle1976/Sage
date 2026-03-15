from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GrowingPlanItem(Base):
    __tablename__ = "growing_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_spec_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plant_specs.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), server_default="queued")
    optimal_sow_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    optimal_sow_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    suggested_alternative_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plant_specs.id"), nullable=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
