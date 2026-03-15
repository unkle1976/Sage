import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlantSpec(Base):
    __tablename__ = "plant_specs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    common_name: Mapped[str] = mapped_column(String(100))
    botanical_name: Mapped[str | None] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(30))  # vegetable, herb, fruit, edible_flower
    uk_hardiness: Mapped[str | None] = mapped_column(String(20))  # hardy, half_hardy, tender
    growing_difficulty: Mapped[str | None] = mapped_column(String(20))  # beginner, intermediate, advanced
    soil_preferences: Mapped[dict | None] = mapped_column(JSONB)
    sun_requirements: Mapped[str | None] = mapped_column(String(20))
    water_needs: Mapped[str | None] = mapped_column(String(10))  # low, moderate, high
    spacing_cm: Mapped[dict | None] = mapped_column(JSONB)
    days_to_germination_min: Mapped[int | None] = mapped_column(Integer)
    days_to_germination_max: Mapped[int | None] = mapped_column(Integer)
    days_to_harvest_min: Mapped[int | None] = mapped_column(Integer)
    days_to_harvest_max: Mapped[int | None] = mapped_column(Integer)
    common_pests: Mapped[dict | None] = mapped_column(JSONB)
    common_diseases: Mapped[dict | None] = mapped_column(JSONB)
    companion_plants: Mapped[dict | None] = mapped_column(JSONB)
    antagonist_plants: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    growth_milestones: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    interesting_facts: Mapped[list | None] = mapped_column(JSONB, nullable=True)
