import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    garden_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gardens.id", ondelete="CASCADE"), index=True)
    plant_spec_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plant_specs.id"), index=True)
    variety: Mapped[str | None] = mapped_column(String(100))
    location_description: Mapped[str | None] = mapped_column(String(200))
    planting_date: Mapped[date | None] = mapped_column(Date)
    planting_method: Mapped[str | None] = mapped_column(String(30))
    growth_stage: Mapped[str] = mapped_column(String(30), default="seed")
    health_status: Mapped[str] = mapped_column(String(20), default="healthy")
    health_score: Mapped[int] = mapped_column(SmallInteger, default=100)
    notes: Mapped[dict | None] = mapped_column(JSONB)
    harvest_log: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
