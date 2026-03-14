import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.user import User
from app.services.onboarding import OnboardingService


@pytest.fixture
def onboarding():
    postcode_service = MagicMock()
    soil_service = MagicMock()
    return OnboardingService(
        postcode_service=postcode_service,
        soil_service=soil_service,
    )


@pytest.mark.asyncio
async def test_welcome_message_asks_what_to_grow(onboarding):
    msg = await onboarding.get_welcome_message()
    assert "grow" in msg.lower()
    assert "postcode" not in msg.lower()


def test_steps_are_three(onboarding):
    assert onboarding.STEPS == ["awaiting_first_plant", "awaiting_postcode", "complete"]


@pytest.mark.asyncio
async def test_handle_first_plant_asks_postcode(onboarding):
    user = User(
        id=uuid.uuid4(),
        whatsapp_phone="07000000000",
        onboarding_step="awaiting_first_plant",
    )
    session = AsyncMock()

    response = await onboarding.process_step(user, "tomatoes", session)

    assert "postcode" in response.lower()
    assert user.onboarding_step == "awaiting_postcode"


@pytest.mark.asyncio
async def test_handle_postcode_completes_onboarding(onboarding):
    user = User(
        id=uuid.uuid4(),
        whatsapp_phone="07000000000",
        onboarding_step="awaiting_postcode",
        preferences={"first_plant": "tomatoes"},
    )
    session = AsyncMock()

    onboarding.postcode_service.lookup = AsyncMock(return_value={
        "outward_code": "DN35",
        "latitude": 53.56,
        "longitude": -0.05,
        "region": "Yorkshire and The Humber",
        "admin_district": "North East Lincolnshire",
    })
    onboarding.soil_service.get_soil_type = AsyncMock(return_value={
        "soil_type": "silty clay",
    })

    # Mock DB query for plant spec matching (returns no matches)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    response = await onboarding.process_step(user, "DN35", session)

    assert user.onboarding_complete is True
    assert user.onboarding_step == "complete"
    # No numbered lists
    assert "1." not in response
    assert "2." not in response


@pytest.mark.asyncio
async def test_handle_postcode_invalid_retries(onboarding):
    user = User(
        id=uuid.uuid4(),
        whatsapp_phone="07000000000",
        onboarding_step="awaiting_postcode",
        preferences={"first_plant": "tomatoes"},
    )
    session = AsyncMock()
    onboarding.postcode_service.lookup = AsyncMock(return_value=None)

    response = await onboarding.process_step(user, "ZZZZZ", session)

    assert user.onboarding_step == "awaiting_postcode"
    assert "try again" in response.lower() or "couldn't find" in response.lower()
