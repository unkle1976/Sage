import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PhotoRecord(Base):
    __tablename__ = "photo_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    thumbnail_key: Mapped[str | None] = mapped_column(String(255))
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cv_analysis: Mapped[dict | None] = mapped_column(JSONB)
    cv_model_version: Mapped[str | None] = mapped_column(String(20))
    whatsapp_media_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
