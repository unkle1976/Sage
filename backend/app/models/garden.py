import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, String, Boolean, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Garden(Base):
    __tablename__ = "gardens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    size_sqm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    orientation: Mapped[str | None] = mapped_column(String(20))
    garden_type: Mapped[str | None] = mapped_column(String(30))  # back_garden, allotment, balcony
    growing_methods: Mapped[dict | None] = mapped_column(JSONB)
    microclimate_notes: Mapped[dict | None] = mapped_column(JSONB)
    water_source: Mapped[str | None] = mapped_column(String(20))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
