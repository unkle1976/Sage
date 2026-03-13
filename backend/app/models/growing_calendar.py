import uuid

from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GrowingCalendar(Base):
    __tablename__ = "growing_calendar"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plant_spec_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plant_specs.id", ondelete="CASCADE"), index=True)
    uk_region: Mapped[str] = mapped_column(String(50))
    activity: Mapped[str] = mapped_column(String(30))  # sow_indoors, sow_outdoors, transplant, harvest_begin
    month_start: Mapped[int] = mapped_column(SmallInteger)
    month_end: Mapped[int] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
