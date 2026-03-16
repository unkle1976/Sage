import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContextEvent(Base):
    __tablename__ = "context_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    garden_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gardens.id", ondelete="CASCADE"))
    plant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    source_agent: Mapped[str | None] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict | None] = mapped_column(JSONB)
    weather_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    reasoning_trace: Mapped[str | None] = mapped_column(Text)
    related_events: Mapped[dict | None] = mapped_column(JSONB)  # array of UUIDs
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    outcome_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
