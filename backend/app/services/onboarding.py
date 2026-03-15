import re
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement_profile import EngagementProfile
from app.models.garden import Garden
from app.models.growing_season import GrowingSeason
from app.models.plant import Plant
from app.models.plant_spec import PlantSpec
from app.models.user import User
from app.services.postcode import PostcodeService
from app.services.soil import SoilService


class OnboardingService:
    """Value-first onboarding: 3 messages to get growing.

    Flow:
      1. Sage asks what they want to grow (the exciting bit)
      2. User says a plant → Sage gives seasonal value + asks postcode
      3. User gives postcode → Sage gives location-specific first task → DONE
    """

    STEPS = [
        "awaiting_first_plant",
        "awaiting_postcode",
        "complete",
    ]

    def __init__(self, postcode_service: PostcodeService, soil_service: SoilService):
        self.postcode_service = postcode_service
        self.soil_service = soil_service

    async def get_welcome_message(self) -> str:
        """First message — ask what they want to grow. That's it."""
        return (
            "Hey! I'm Sage, your gardening coach \U0001f331 "
            "What are you thinking of growing?"
        )

    async def process_step(self, user: User, message: str, session: AsyncSession) -> str:
        """Process user input for current onboarding step."""
        step = user.onboarding_step or "awaiting_first_plant"

        if step == "awaiting_first_plant":
            return await self._handle_first_plant(user, message, session)
        elif step == "awaiting_postcode":
            return await self._handle_postcode(user, message, session)
        else:
            return "You're all set! Just message me anytime about your garden."

    async def _handle_first_plant(self, user: User, message: str, session: AsyncSession) -> str:
        """User told us what they want to grow. Store it, give value, ask postcode."""
        plant_names = self._parse_plant_names(message)
        plant_text = ", ".join(plant_names) if plant_names else message.strip()

        # Store plant intent in preferences for later
        user.preferences = user.preferences or {}
        user.preferences["first_plant"] = plant_text

        user.onboarding_step = "awaiting_postcode"
        await session.commit()

        # Give seasonal value + ask for postcode with context
        month = datetime.now().strftime("%B")

        return (
            f"Nice one! {month} is a great time to get started. "
            f"Whereabouts in the UK are you? Just your postcode area is fine, "
            f"like B44 or DN35 \u2014 I need it for weather and frost dates"
        )

    async def _handle_postcode(self, user: User, message: str, session: AsyncSession) -> str:
        """User gave postcode. Look up location, create garden, give first task."""
        postcode = message.strip()
        result = await self.postcode_service.lookup(postcode)

        if not result:
            return (
                "Hmm, I couldn't find that postcode. Could you try again? "
                "Something like 'BS3 1AB' or just the first part like 'BS3'"
            )

        # Store location
        user.postcode_outward = result["outward_code"]
        user.latitude = result["latitude"]
        user.longitude = result["longitude"]
        user.uk_region = result.get("admin_district") or result.get("region")

        # Look up soil
        soil = await self.soil_service.get_soil_type(
            result["latitude"],
            result["longitude"],
            admin_district=result.get("admin_district"),
            region=result.get("region"),
        )
        user.soil_type = soil.get("soil_type", "unknown")

        # Default experience to beginner (inferred later through conversation)
        user.experience_level = "beginner"

        # Create garden (default to back garden — refined later through conversation)
        garden = Garden(
            user_id=user.id,
            name="My garden",
            garden_type="back_garden",
            is_primary=True,
        )
        session.add(garden)

        # Match plants from user's first message
        plant_text = (user.preferences or {}).get("first_plant", "")
        plant_names = self._parse_plant_names(plant_text) if plant_text else []
        await self._create_plants(plant_names, user, garden, session)

        # Create engagement profile
        profile = EngagementProfile(
            user_id=user.id,
            preferred_time="morning",
            notification_level="normal",
        )
        session.add(profile)

        # Create growing season
        current_year = date.today().year
        season = GrowingSeason(
            user_id=user.id,
            year=current_year,
            label=f"Spring/Summer {current_year}",
            started_at=date.today(),
        )
        session.add(season)

        # Complete onboarding
        user.onboarding_complete = True
        user.onboarding_step = "complete"
        await session.commit()

        # Build response with location-specific first task
        location = result.get("admin_district") or result.get("region") or "your area"
        soil_desc = user.soil_type if user.soil_type != "unknown" else "local"

        return (
            f"{location} \u2014 nice! Your soil's {soil_desc} round there. "
            f"Right, I'm all set up for you. I'll send you a message whenever "
            f"your plants need attention \u2014 watering, planting out, weather "
            f"warnings, that sort of thing. You don't need to remember, I'll "
            f"keep track for you \U0001f331"
        )

    async def _create_plants(self, plant_names, user, garden, session):
        """Match plant names to PlantSpec and create Plant records."""
        if not plant_names:
            return

        search_variants = {}
        for name in plant_names:
            lower = name.lower()
            search_variants[lower] = name
            if lower.endswith("oes"):
                search_variants[lower[:-2]] = name
            elif lower.endswith("ies"):
                search_variants[lower[:-3] + "y"] = name
            elif lower.endswith("s") and not lower.endswith("ss"):
                search_variants[lower[:-1]] = name

        conditions = [func.lower(PlantSpec.common_name) == v for v in search_variants]
        if conditions:
            stmt = select(PlantSpec).where(or_(*conditions))
            result = await session.execute(stmt)
            matched_specs = result.scalars().all()

            for spec in matched_specs:
                plant = Plant(
                    garden_id=garden.id,
                    plant_spec_id=spec.id,
                    variety=spec.common_name,
                )
                session.add(plant)

    @staticmethod
    def _parse_plant_names(text: str) -> list[str]:
        """Parse comma and 'and'-separated plant names from free text."""
        normalised = re.sub(r"\band\b", ",", text, flags=re.IGNORECASE)
        parts = [part.strip() for part in normalised.split(",")]
        return [p for p in parts if p]
