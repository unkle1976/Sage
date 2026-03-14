import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GrowingSeason(Base):
    __tablename__ = "growing_seasons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(SmallInteger, index=True)
    label: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[date] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)
    season_summary: Mapped[dict | None] = mapped_column(JSONB)
    weather_summary: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
