import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
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
    growing_season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("growing_seasons.id"), index=True)
    parent_plant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plants.id"))
    seed_source: Mapped[str | None] = mapped_column(String(30))
    final_outcome: Mapped[str | None] = mapped_column(String(20))
    yield_total_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    season_notes: Mapped[str | None] = mapped_column(Text)
    next_milestone_index: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    next_milestone_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    milestone_delayed: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
