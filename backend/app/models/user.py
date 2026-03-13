import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, String, Boolean, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    whatsapp_phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(100))
    postcode_outward: Mapped[str | None] = mapped_column(String(4))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    uk_region: Mapped[str | None] = mapped_column(String(50))
    soil_type: Mapped[str | None] = mapped_column(String(50))
    experience_level: Mapped[str | None] = mapped_column(String(20))  # novice, intermediate, experienced
    subscription_tier: Mapped[str] = mapped_column(String(10), default="free")  # free, premium
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_step: Mapped[str | None] = mapped_column(String(50))
    preferences: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
