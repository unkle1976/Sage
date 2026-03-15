import logging
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

logger = logging.getLogger(__name__)

# Map colloquial / plural plant names to PlantSpec common_name values.
# A value of None means the term is a category (e.g. "herbs") — skip it,
# individual herb species will be matched by their own names.
COLLOQUIAL_ALIASES: dict[str, str | None] = {
    "chillies": "chilli pepper",
    "chilli": "chilli pepper",
    "chilis": "chilli pepper",
    "peppers": "pepper",
    "toms": "tomato",
    "tomatoes": "tomato",
    "spuds": "potato",
    "potatoes": "potato",
    "courgettes": "courgette",
    "runner beans": "runner bean",
    "broad beans": "broad bean",
    "french beans": "french bean",
    "spring onions": "spring onion",
    "herbs": None,
    "salad": "lettuce",
    "lettuce": "lettuce",
    "strawberries": "strawberry",
    "raspberries": "raspberry",
    "blueberries": "blueberry",
    "carrots": "carrot",
    "beetroot": "beetroot",
    "radishes": "radish",
    "peas": "pea",
    "sweetcorn": "sweetcorn",
}

# Keywords that suggest the message is about gardening / growing
_GARDENING_KEYWORDS = {
    "grow", "growing", "plant", "plants", "planting", "garden", "gardening",
    "veg", "vegetable", "vegetables", "fruit", "fruits", "seed", "seeds",
    "sow", "sowing", "harvest", "allotment", "plot", "raised bed",
    "compost", "soil", "pot", "pots", "container", "greenhouse",
    "tomato", "tomatoes", "carrot", "carrots", "potato", "potatoes",
    "herb", "herbs", "basil", "mint", "parsley", "chilli", "chillies",
    "lettuce", "salad", "strawberry", "strawberries", "raspberry",
    "raspberries", "blueberry", "blueberries", "courgette", "cucumber",
    "bean", "beans", "pea", "peas", "onion", "garlic", "leek",
    "beetroot", "radish", "sweetcorn", "flower", "flowers", "weed",
    "prune", "pruning", "mulch", "fertiliser", "fertilizer",
    "sunlight", "watering", "shed", "lawn", "hedge",
}


class OnboardingService:
    """Value-first onboarding: 3 messages to get growing.

    Flow:
      1. Sage asks what they want to grow (the exciting bit)
      2. User says a plant → Sage gives seasonal value + asks postcode
      3. User gives postcode → Sage confirms location, references their plant,
         and kicks straight into coaching (seeds? equipment? first task)
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

        # Friendly redirect if the message is clearly not about gardening
        if step in ("awaiting_first_plant", "awaiting_postcode") and self._is_off_topic(message):
            return (
                "Ha, I'm just a gardening coach! But if you fancy growing "
                "something, I'm your person \U0001f331 What sounds good?"
            )

        if step == "awaiting_first_plant":
            return await self._handle_first_plant(user, message, session)
        elif step == "awaiting_postcode":
            return await self._handle_postcode(user, message, session)
        else:
            return "You're all set! Just message me anytime about your garden."

    async def _handle_first_plant(self, user: User, message: str, session: AsyncSession) -> str:
        """User told us what they want to grow. Store it, give value, ask postcode."""
        # Store raw message — we'll extract plant names later when we have PlantSpec access
        user.preferences = user.preferences or {}
        user.preferences["first_plant_raw"] = message.strip()

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
        postcode = self._extract_postcode(message)
        result = await self.postcode_service.lookup(postcode) if postcode else None

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

        # Match plants from user's first message using fuzzy matching
        # Check both keys for backward compatibility (old code stored as "first_plant")
        prefs = user.preferences or {}
        raw_text = prefs.get("first_plant_raw", "") or prefs.get("first_plant", "")
        matched_specs = await self._match_plants_from_text(raw_text, session)
        matched_names = []
        for spec in matched_specs:
            plant = Plant(
                garden_id=garden.id,
                plant_spec_id=spec.id,
                variety=spec.common_name,
            )
            session.add(plant)
            matched_names.append(spec.common_name.lower())

        # Store clean matched names in preferences
        user.preferences = user.preferences or {}
        user.preferences["first_plants"] = matched_names

        logger.info(
            "Onboarding plant match: raw=%r matched=%r",
            raw_text,
            matched_names,
        )

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

        # Build response — location confirmation then straight into coaching
        location = result.get("admin_district") or result.get("region") or "your area"
        soil_desc = user.soil_type if user.soil_type != "unknown" else "local"

        if matched_names:
            plant_list = " and ".join(matched_names)
            return (
                f"{location} \u2014 nice! Your soil's {soil_desc} round there. "
                f"Right, let's get your {plant_list} going. "
                f"Have you got seeds already or do you need to grab some?"
            )
        else:
            # Couldn't match to a known plant — ask Claude to take over
            return (
                f"{location} \u2014 nice! Your soil's {soil_desc} round there. "
                f"I'm all set up for you. So tell me more about what you'd like to grow "
                f"and I'll get you started \U0001f331"
            )

    async def _match_plants_from_text(
        self, text: str, session: AsyncSession
    ) -> list[PlantSpec]:
        """Fuzzy-match plant names from free text against PlantSpec database.

        Instead of parsing the user's message into plant names (which fails for
        natural language like "I'm thinking carrots!"), we load all PlantSpec
        common names and check which ones appear as substrings in the message.
        """
        if not text:
            return []

        text_lower = text.lower()

        # Resolve colloquial aliases — replace known slang/plurals with
        # canonical PlantSpec names so the regex matching can find them.
        # Process multi-word aliases first (longest-first) to avoid partial
        # replacements like "broad" matching before "broad beans".
        sorted_aliases = sorted(COLLOQUIAL_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, text_lower):
                canonical = COLLOQUIAL_ALIASES[alias]
                if canonical is None:
                    # Category term (e.g. "herbs") — just remove it so it
                    # doesn't interfere, individual species matched separately
                    continue
                text_lower = re.sub(pattern, canonical, text_lower)

        # Load all plant spec names
        stmt = select(PlantSpec)
        result = await session.execute(stmt)
        all_specs = result.scalars().all()

        matched = []
        for spec in all_specs:
            name = spec.common_name.lower()
            # Check if plant name appears in user's message (word boundary aware)
            # e.g. "carrot" matches in "I'm thinking carrots!" but "car" won't match "carrots"
            # Also check common plural forms
            variants = [name]
            if name.endswith("o"):
                variants.append(name + "es")  # tomato → tomatoes
            if name.endswith("y"):
                variants.append(name[:-1] + "ies")  # strawberry → strawberries
            if name[-1] not in ("s", "h", "x"):
                variants.append(name + "s")  # carrot → carrots
            if name.endswith("ch") or name.endswith("sh"):
                variants.append(name + "es")  # radish → radishes

            for variant in variants:
                # Word boundary check — ensure we match whole words
                pattern = r'\b' + re.escape(variant) + r'\b'
                if re.search(pattern, text_lower):
                    matched.append(spec)
                    break

        return matched

    @staticmethod
    def _extract_postcode(text: str) -> str:
        """Extract a UK postcode from free text.

        Handles:
          - Full postcode: "BS3 1AB", "bs31ab"
          - Outward code: "BS3", "DN35"
          - Embedded in text: "i'm in bristol, BS3 1AB"
          - Just the text as-is (fallback)
        """
        text = text.strip()

        # Try full UK postcode pattern first (e.g. "BS3 1AB" or "BS31AB")
        full_match = re.search(
            r'\b([A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2})\b',
            text,
        )
        if full_match:
            return full_match.group(1).strip()

        # Try outward code only (e.g. "BS3", "DN35", "EC1")
        out_match = re.search(
            r'\b([A-Za-z]{1,2}\d[A-Za-z\d]?)\b',
            text,
        )
        if out_match:
            return out_match.group(1).strip()

        # Fallback: return the whole message (let the postcode service handle it)
        return text

    @staticmethod
    def _is_off_topic(text: str) -> bool:
        """Return True if the message is clearly not about gardening.

        Keeps it lightweight — just keyword presence checks, no API call.
        If in doubt (short messages, ambiguous), returns False so normal
        onboarding proceeds.
        """
        text_lower = text.lower()

        # Very short messages (1-3 chars) are likely postcodes or typos — not off-topic
        stripped = text.strip()
        if len(stripped) <= 3:
            return False

        # If it looks like a UK postcode, not off-topic
        if re.search(r'\b[A-Za-z]{1,2}\d[A-Za-z\d]?\s*(\d[A-Za-z]{2})?\b', stripped):
            return False

        # Check for any gardening-related keyword
        for keyword in _GARDENING_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                return False

        # Check against colloquial aliases too
        for alias in COLLOQUIAL_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return False

        # Nothing gardening-related found — likely off-topic
        return True

    @staticmethod
    def _parse_plant_names(text: str) -> list[str]:
        """Parse comma and 'and'-separated plant names from free text.

        Used for clean input like "tomatoes, basil and peppers".
        For natural language, use _match_plants_from_text instead.
        """
        normalised = re.sub(r"\band\b", ",", text, flags=re.IGNORECASE)
        parts = [part.strip() for part in normalised.split(",")]
        return [p for p in parts if p]
