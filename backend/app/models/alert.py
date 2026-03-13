import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"))
    alert_type: Mapped[str] = mapped_column(String(50))  # frost_warning, watering_reminder
    priority: Mapped[str] = mapped_column(String(10))  # low, medium, high, urgent
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending")
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(100))
    message_content: Mapped[str | None] = mapped_column(Text)
    user_response: Mapped[dict | None] = mapped_column(JSONB)
    source_agent: Mapped[str | None] = mapped_column(String(50))
    reasoning: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
