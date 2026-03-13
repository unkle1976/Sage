import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    badge_type: Mapped[str] = mapped_column(String(50))
    badge_tier: Mapped[str] = mapped_column(String(10))  # bronze, silver, gold
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    season: Mapped[str | None] = mapped_column(String(20))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
