import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.onboarding import OnboardingService
from app.models.user import User


@pytest.fixture
def mock_postcode():
    service = MagicMock()
    service.lookup = AsyncMock(return_value={
        "postcode": "BS3 1AB",
        "outward_code": "BS3",
        "latitude": 51.438,
        "longitude": -2.604,
        "region": "South West",
        "admin_district": "Bristol",
    })
    return service


@pytest.fixture
def mock_soil():
    service = MagicMock()
    service.get_soil_type = AsyncMock(return_value={"soil_type": "clay", "source": "bgs"})
    return service


@pytest.fixture
def onboarding(mock_postcode, mock_soil):
    return OnboardingService(postcode_service=mock_postcode, soil_service=mock_soil)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def new_user():
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_postcode")
    user.id = uuid.uuid4()
    return user


# --- Welcome message ---

async def test_welcome_message(onboarding):
    msg = await onboarding.get_welcome_message()
    assert "Sage" in msg
    assert "postcode" in msg


# --- Step 1: Postcode ---

async def test_postcode_step_success(onboarding, new_user, mock_session):
    response = await onboarding.process_step(new_user, "BS3 1AB", mock_session)
    assert "Bristol" in response  # Uses admin_district for hyper-local naming
    assert "clay" in response
    assert new_user.onboarding_step == "awaiting_garden_type"
    assert new_user.postcode_outward == "BS3"
    assert new_user.uk_region == "Bristol"  # admin_district, not region
    assert new_user.soil_type == "clay"
    mock_session.commit.assert_awaited_once()


async def test_postcode_step_invalid(onboarding, mock_postcode, new_user, mock_session):
    mock_postcode.lookup = AsyncMock(return_value=None)
    response = await onboarding.process_step(new_user, "ZZZZZ", mock_session)
    assert "couldn't find" in response
    assert new_user.onboarding_step == "awaiting_postcode"


async def test_postcode_step_unknown_soil(onboarding, mock_soil, new_user, mock_session):
    mock_soil.get_soil_type = AsyncMock(return_value={"soil_type": "unknown", "source": "default"})
    response = await onboarding.process_step(new_user, "BS3 1AB", mock_session)
    assert "local" in response  # Should say "local" not "unknown"
    assert new_user.onboarding_step == "awaiting_garden_type"


# --- Step 2: Garden type ---

async def test_garden_type_by_number(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_garden_type")
    user.id = uuid.uuid4()
    response = await onboarding.process_step(user, "1", mock_session)
    assert "experience" in response.lower()
    assert user.onboarding_step == "awaiting_experience"
    # Garden record should be created via session.add
    mock_session.add.assert_called_once()
    garden = mock_session.add.call_args[0][0]
    assert garden.garden_type == "back_garden"


async def test_garden_type_by_text(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_garden_type")
    user.id = uuid.uuid4()
    response = await onboarding.process_step(user, "allotment", mock_session)
    assert user.onboarding_step == "awaiting_experience"
    garden = mock_session.add.call_args[0][0]
    assert garden.garden_type == "allotment"


async def test_garden_type_invalid(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_garden_type")
    user.id = uuid.uuid4()
    response = await onboarding.process_step(user, "spaceship", mock_session)
    assert user.onboarding_step == "awaiting_garden_type"
    assert "pick" in response.lower() or "try" in response.lower() or "choose" in response.lower()


# --- Step 3: Experience ---

async def test_experience_by_keyword(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_experience")
    response = await onboarding.process_step(user, "beginner", mock_session)
    assert user.experience_level == "beginner"
    assert user.onboarding_step == "awaiting_plants"
    assert "grow" in response.lower() or "what" in response.lower()


async def test_experience_by_number(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_experience")
    response = await onboarding.process_step(user, "2", mock_session)
    assert user.experience_level == "intermediate"
    assert user.onboarding_step == "awaiting_plants"


async def test_experience_invalid(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_experience")
    response = await onboarding.process_step(user, "astronaut", mock_session)
    assert user.onboarding_step == "awaiting_experience"
    assert user.experience_level is None


# --- Step 4: Plants ---

async def test_plants_with_matches(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_plants")
    user.id = uuid.uuid4()
    user.experience_level = "beginner"
    user.uk_region = "South West"
    user.soil_type = "clay"

    # Mock PlantSpec query result
    tomato_spec = MagicMock()
    tomato_spec.id = uuid.uuid4()
    tomato_spec.common_name = "Tomato"

    basil_spec = MagicMock()
    basil_spec.id = uuid.uuid4()
    basil_spec.common_name = "Basil"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tomato_spec, basil_spec]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Need a garden for the user
    garden = MagicMock()
    garden.id = uuid.uuid4()
    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden
    # First call = plant spec lookup, second call = garden lookup
    mock_session.execute = AsyncMock(side_effect=[mock_result, mock_garden_result])

    response = await onboarding.process_step(user, "tomatoes and basil", mock_session)
    assert user.onboarding_complete is True
    assert user.onboarding_step == "complete"
    assert "set" in response.lower() or "\U0001f389" in response


async def test_plants_no_matches(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_plants")
    user.id = uuid.uuid4()
    user.experience_level = "beginner"
    user.uk_region = "South West"
    user.soil_type = "clay"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_garden_result = MagicMock()
    garden = MagicMock()
    garden.id = uuid.uuid4()
    mock_garden_result.scalar_one_or_none.return_value = garden
    mock_session.execute = AsyncMock(side_effect=[mock_result, mock_garden_result])

    response = await onboarding.process_step(user, "moon fruit", mock_session)
    assert user.onboarding_complete is True
    assert "couldn't find" in response.lower() or "don't recognise" in response.lower() or "moon fruit" in response.lower()


async def test_plants_partial_matches(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_plants")
    user.id = uuid.uuid4()
    user.experience_level = "intermediate"
    user.uk_region = "South West"
    user.soil_type = "clay"

    tomato_spec = MagicMock()
    tomato_spec.id = uuid.uuid4()
    tomato_spec.common_name = "Tomato"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tomato_spec]
    garden = MagicMock()
    garden.id = uuid.uuid4()
    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden
    mock_session.execute = AsyncMock(side_effect=[mock_result, mock_garden_result])

    response = await onboarding.process_step(user, "tomatoes, unicorn berries", mock_session)
    assert user.onboarding_complete is True
    # Should mention the unrecognised plant
    assert "unicorn berries" in response.lower()


# --- Already complete ---

async def test_already_complete(onboarding, mock_session):
    user = User(whatsapp_phone="447700900000", onboarding_step="complete", onboarding_complete=True)
    response = await onboarding.process_step(user, "hello", mock_session)
    assert "already" in response.lower() or "set up" in response.lower()


# --- Plant name parsing ---

def test_parse_plant_names(onboarding):
    assert onboarding._parse_plant_names("tomatoes, basil, and courgettes") == ["tomatoes", "basil", "courgettes"]
    assert onboarding._parse_plant_names("tomatoes and basil") == ["tomatoes", "basil"]
    assert onboarding._parse_plant_names("just tomatoes") == ["just tomatoes"]
    assert onboarding._parse_plant_names("peas, beans, carrots, and lettuce") == ["peas", "beans", "carrots", "lettuce"]


# --- Plural matching ---

async def test_plants_plural_forms_matched(onboarding, mock_session):
    """User types 'tomatoes' (plural) and DB has 'Tomato' (singular) — should match."""
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_plants")
    user.id = uuid.uuid4()
    user.experience_level = "beginner"
    user.uk_region = "London"
    user.soil_type = "clay"

    tomato_spec = MagicMock()
    tomato_spec.id = uuid.uuid4()
    tomato_spec.common_name = "Tomato"

    courgette_spec = MagicMock()
    courgette_spec.id = uuid.uuid4()
    courgette_spec.common_name = "Courgette"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tomato_spec, courgette_spec]
    garden = MagicMock()
    garden.id = uuid.uuid4()
    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden
    mock_session.execute = AsyncMock(side_effect=[mock_result, mock_garden_result])

    response = await onboarding.process_step(user, "tomatoes and courgettes", mock_session)
    assert user.onboarding_complete is True
    # Both should be matched — no "don't recognise" message
    assert "don't recognise" not in response.lower()
    assert "Tomato" in response
    assert "Courgette" in response


async def test_plants_berries_plural(onboarding, mock_session):
    """'strawberries' → 'strawberry' should match Strawberry in DB."""
    user = User(whatsapp_phone="447700900000", onboarding_step="awaiting_plants")
    user.id = uuid.uuid4()
    user.experience_level = "beginner"
    user.uk_region = "South West"
    user.soil_type = "clay"

    strawberry_spec = MagicMock()
    strawberry_spec.id = uuid.uuid4()
    strawberry_spec.common_name = "Strawberry"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [strawberry_spec]
    garden = MagicMock()
    garden.id = uuid.uuid4()
    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden
    mock_session.execute = AsyncMock(side_effect=[mock_result, mock_garden_result])

    response = await onboarding.process_step(user, "strawberries", mock_session)
    assert user.onboarding_complete is True
    assert "don't recognise" not in response.lower()
