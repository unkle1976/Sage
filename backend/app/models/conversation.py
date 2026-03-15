import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user, assistant
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(20), server_default="cli")  # cli, slack, whatsapp

    def __init__(self, **kwargs):
        kwargs.setdefault("channel", "cli")
        super().__init__(**kwargs)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
