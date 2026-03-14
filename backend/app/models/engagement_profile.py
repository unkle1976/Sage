import uuid
from datetime import datetime, time as time_type

from sqlalchemy import DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EngagementProfile(Base):
    __tablename__ = "engagement_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    preferred_time: Mapped[str] = mapped_column(String(20), default="morning", insert_default="morning")
    notification_level: Mapped[str] = mapped_column(String(20), default="normal", insert_default="normal")

    def __init__(self, **kwargs):
        kwargs.setdefault("preferred_time", "morning")
        kwargs.setdefault("notification_level", "normal")
        super().__init__(**kwargs)
    quiet_hours_start: Mapped[time_type | None] = mapped_column(Time)
    quiet_hours_end: Mapped[time_type | None] = mapped_column(Time)
    last_sage_initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_user_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
