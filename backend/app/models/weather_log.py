import uuid
from datetime import date as date_type

from sqlalchemy import Boolean, Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WeatherLog(Base):
    __tablename__ = "weather_logs"
    __table_args__ = (
        UniqueConstraint("postcode_outward", "date", name="uq_weather_postcode_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    postcode_outward: Mapped[str] = mapped_column(String(4), index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)
    temp_max_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    temp_min_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    rainfall_mm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    wind_max_kmh: Mapped[float | None] = mapped_column(Numeric(4, 1))
    sunshine_hours: Mapped[float | None] = mapped_column(Numeric(3, 1))
    frost: Mapped[bool] = mapped_column(Boolean, default=False)
