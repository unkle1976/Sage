import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.garden import Garden
from app.models.plant import Plant
from app.models.plant_spec import PlantSpec
from app.models.user import User
from app.services.postcode import PostcodeService
from app.services.soil import SoilService


class OnboardingService:
    """State machine guiding new users through garden setup via conversation steps."""

    STEPS = [
        "awaiting_postcode",
        "awaiting_garden_type",
        "awaiting_experience",
        "awaiting_plants",
        "complete",
    ]

    GARDEN_TYPES = {
        "1": "back_garden",
        "back garden": "back_garden",
        "back_garden": "back_garden",
        "2": "allotment",
        "allotment": "allotment",
        "3": "front_garden",
        "front garden": "front_garden",
        "front_garden": "front_garden",
        "4": "balcony",
        "balcony": "balcony",
        "patio": "balcony",
        "balcony/patio": "balcony",
        "5": "windowsill",
        "windowsill": "windowsill",
        "window sill": "windowsill",
        "6": "community_garden",
        "community garden": "community_garden",
        "community_garden": "community_garden",
    }

    EXPERIENCE_LEVELS = {
        "1": "beginner",
        "beginner": "beginner",
        "just starting": "beginner",
        "just starting out": "beginner",
        "new": "beginner",
        "2": "intermediate",
        "intermediate": "intermediate",
        "few seasons": "intermediate",
        "a few seasons": "intermediate",
        "some": "intermediate",
        "3": "experienced",
        "experienced": "experienced",
        "been at it": "experienced",
        "years": "experienced",
        "expert": "experienced",
    }

    GARDEN_TYPE_LABELS = {
        "back_garden": "back garden",
        "allotment": "allotment",
        "front_garden": "front garden",
        "balcony": "balcony/patio",
        "windowsill": "windowsill",
        "community_garden": "community garden",
    }

    def __init__(self, postcode_service: PostcodeService, soil_service: SoilService):
        self.postcode_service = postcode_service
        self.soil_service = soil_service

    async def get_welcome_message(self) -> str:
        """Return the initial onboarding greeting."""
        return (
            "Hello! I'm Sage, your gardening companion \U0001f331 "
            "To give you the best advice, I need to know where you're growing. "
            "Could you share your postcode? (I only store the first part, like BS3 "
            "\u2014 just enough for local weather and soil)"
        )

    async def process_step(self, user: User, message: str, session: AsyncSession) -> str:
        """Process user input for current onboarding step. Returns Sage's response."""
        step = user.onboarding_step or "awaiting_postcode"

        if step == "awaiting_postcode":
            return await self._handle_postcode(user, message, session)
        elif step == "awaiting_garden_type":
            return await self._handle_garden_type(user, message, session)
        elif step == "awaiting_experience":
            return await self._handle_experience(user, message, session)
        elif step == "awaiting_plants":
            return await self._handle_plants(user, message, session)
        else:
            return "You're already set up! Just ask me anything about your garden."

    # ---- Step handlers ----

    async def _handle_postcode(self, user: User, message: str, session: AsyncSession) -> str:
        postcode = message.strip()
        result = await self.postcode_service.lookup(postcode)

        if not result:
            return (
                "Hmm, I couldn't find that postcode. Could you try again? "
                "Something like 'BS3 1AB' or just the first part like 'BS3'."
            )

        user.postcode_outward = result["outward_code"]
        user.latitude = result["latitude"]
        user.longitude = result["longitude"]
        # Use admin_district for hyper-local naming (e.g. "North East Lincolnshire" not "Yorkshire and The Humber")
        user.uk_region = result.get("admin_district") or result["region"]

        soil = await self.soil_service.get_soil_type(
            result["latitude"],
            result["longitude"],
            admin_district=result.get("admin_district"),
            region=result.get("region"),
        )
        user.soil_type = soil.get("soil_type", "unknown")

        user.onboarding_step = "awaiting_garden_type"
        await session.commit()

        soil_desc = user.soil_type if user.soil_type != "unknown" else "local"
        location = result.get("admin_district") or result["region"]
        return (
            f"Lovely! I can see you're in {location} with {soil_desc} soil. "
            "Now, what kind of growing space have you got?\n\n"
            "1. Back garden\n"
            "2. Allotment\n"
            "3. Front garden\n"
            "4. Balcony/patio\n"
            "5. Windowsill\n"
            "6. Community garden"
        )

    async def _handle_garden_type(self, user: User, message: str, session: AsyncSession) -> str:
        key = message.strip().lower()
        garden_type = self.GARDEN_TYPES.get(key)

        if not garden_type:
            return (
                "I didn't quite get that \u2014 could you pick a number (1\u20136) or type "
                "the name? For example, '1' or 'back garden'."
            )

        label = self.GARDEN_TYPE_LABELS.get(garden_type, garden_type)
        garden = Garden(
            user_id=user.id,
            name=f"My {label}",
            garden_type=garden_type,
            is_primary=True,
        )
        session.add(garden)

        user.onboarding_step = "awaiting_experience"
        await session.commit()

        return (
            "Great! And how would you describe your growing experience?\n\n"
            "1. Just starting out (beginner)\n"
            "2. A few seasons under my belt (intermediate)\n"
            "3. Been at it for years (experienced)"
        )

    async def _handle_experience(self, user: User, message: str, session: AsyncSession) -> str:
        key = message.strip().lower()
        level = self.EXPERIENCE_LEVELS.get(key)

        if not level:
            return (
                "No worries \u2014 just pick a number (1\u20133) or say something like "
                "'beginner', 'intermediate', or 'experienced'."
            )

        user.experience_level = level
        user.onboarding_step = "awaiting_plants"
        await session.commit()

        return (
            "Brilliant! Now, what would you like to grow this year? "
            "Just tell me in your own words \u2014 something like "
            "'tomatoes, courgettes, and some herbs' and I'll get you set up."
        )

    async def _handle_plants(self, user: User, message: str, session: AsyncSession) -> str:
        plant_names = self._parse_plant_names(message)

        # Build search variants: original + stripped plural forms
        search_variants: dict[str, str] = {}  # normalised -> original user input
        for name in plant_names:
            lower = name.lower()
            search_variants[lower] = name
            # Strip common plural suffixes to match DB (e.g. "tomatoes" -> "tomato")
            if lower.endswith("oes"):
                search_variants[lower[:-2]] = name
            elif lower.endswith("ies"):
                search_variants[lower[:-3] + "y"] = name
            elif lower.endswith("s") and not lower.endswith("ss"):
                search_variants[lower[:-1]] = name

        # Search PlantSpec for matches (case-insensitive)
        conditions = [func.lower(PlantSpec.common_name) == variant for variant in search_variants]
        if conditions:
            from sqlalchemy import or_

            stmt = select(PlantSpec).where(or_(*conditions))
            result = await session.execute(stmt)
            matched_specs = result.scalars().all()
        else:
            matched_specs = []

        # Find user's primary garden
        garden_stmt = select(Garden).where(Garden.user_id == user.id, Garden.is_primary.is_(True))
        garden_result = await session.execute(garden_stmt)
        garden = garden_result.scalar_one_or_none()

        # Create Plant records for matches
        matched_names_lower = {spec.common_name.lower() for spec in matched_specs}
        if garden:
            for spec in matched_specs:
                plant = Plant(
                    garden_id=garden.id,
                    plant_spec_id=spec.id,
                    variety=spec.common_name,
                )
                session.add(plant)

        # Identify unrecognised plants — check if any variant of the user's input matched
        unrecognised = []
        for name in plant_names:
            lower = name.lower()
            variants = {lower}
            if lower.endswith("oes"):
                variants.add(lower[:-2])
            elif lower.endswith("ies"):
                variants.add(lower[:-3] + "y")
            elif lower.endswith("s") and not lower.endswith("ss"):
                variants.add(lower[:-1])
            if not variants & matched_names_lower:
                unrecognised.append(name)

        # Complete onboarding
        user.onboarding_complete = True
        user.onboarding_step = "complete"
        await session.commit()

        # Build response
        plant_list = ", ".join(spec.common_name for spec in matched_specs) if matched_specs else "your chosen plants"

        response = (
            f"You're all set! \U0001f389 I've got you down as a {user.experience_level} grower "
            f"in {user.uk_region or 'the UK'} with {user.soil_type or 'local'} soil"
        )

        if matched_specs:
            response += f", growing {plant_list}."
        else:
            response += "."

        response += (
            " I'll start sending you tips and reminders based on your local conditions. "
            "Just message me anytime you've got a question!"
        )

        if unrecognised:
            names = ", ".join(unrecognised)
            response += (
                f"\n\nI don't recognise these yet: {names}. "
                "I'll keep expanding my plant database \u2014 feel free to ask me about them anytime!"
            )

        return response

    # ---- Helpers ----

    @staticmethod
    def _parse_plant_names(text: str) -> list[str]:
        """Parse comma and 'and'-separated plant names from free text."""
        # Replace " and " with comma
        normalised = re.sub(r"\band\b", ",", text, flags=re.IGNORECASE)
        # Split on commas
        parts = [part.strip() for part in normalised.split(",")]
        # Filter empty strings
        return [p for p in parts if p]
