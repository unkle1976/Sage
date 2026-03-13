"""Tests for seed data integrity and seed function."""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.seed_plants import (
    DATA_FILE,
    REGIONS,
    _calendar_entries,
    _plant_dict_to_model,
    load_plants_json,
    seed,
)

# ---------------------------------------------------------------------------
# JSON structure tests
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "common_name",
    "botanical_name",
    "category",
    "uk_hardiness",
    "growing_difficulty",
    "soil_preferences",
    "sun_requirements",
    "water_needs",
    "spacing_cm",
    "days_to_germination_min",
    "days_to_germination_max",
    "days_to_harvest_min",
    "days_to_harvest_max",
    "common_pests",
    "common_diseases",
    "growing_calendar",
}

VALID_CATEGORIES = {"vegetable", "herb", "fruit"}
VALID_HARDINESS = {"hardy", "half_hardy", "tender"}
VALID_DIFFICULTY = {"beginner", "intermediate", "advanced"}
VALID_WATER = {"low", "moderate", "high"}
VALID_ACTIVITIES = {"sow_indoors", "sow_outdoors", "transplant", "harvest"}


@pytest.fixture
def plants_data() -> list[dict]:
    return load_plants_json()


class TestPlantsJsonStructure:
    """Validate the plants.json file has the correct structure."""

    def test_file_exists(self):
        assert DATA_FILE.exists(), f"plants.json not found at {DATA_FILE}"

    def test_is_valid_json(self):
        with open(DATA_FILE) as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_has_50_entries(self, plants_data):
        assert len(plants_data) == 50, f"Expected 50 plants, got {len(plants_data)}"

    def test_unique_common_names(self, plants_data):
        names = [p["common_name"] for p in plants_data]
        assert len(names) == len(set(names)), f"Duplicate names found: {[n for n in names if names.count(n) > 1]}"

    def test_all_required_fields_present(self, plants_data):
        for plant in plants_data:
            missing = REQUIRED_FIELDS - set(plant.keys())
            assert not missing, f"{plant['common_name']} missing fields: {missing}"

    def test_valid_categories(self, plants_data):
        for plant in plants_data:
            assert plant["category"] in VALID_CATEGORIES, (
                f"{plant['common_name']} has invalid category: {plant['category']}"
            )

    def test_valid_hardiness(self, plants_data):
        for plant in plants_data:
            assert plant["uk_hardiness"] in VALID_HARDINESS, (
                f"{plant['common_name']} has invalid hardiness: {plant['uk_hardiness']}"
            )

    def test_valid_difficulty(self, plants_data):
        for plant in plants_data:
            assert plant["growing_difficulty"] in VALID_DIFFICULTY, (
                f"{plant['common_name']} has invalid difficulty: {plant['growing_difficulty']}"
            )

    def test_valid_water_needs(self, plants_data):
        for plant in plants_data:
            assert plant["water_needs"] in VALID_WATER, (
                f"{plant['common_name']} has invalid water_needs: {plant['water_needs']}"
            )

    def test_growing_calendar_has_all_regions(self, plants_data):
        for plant in plants_data:
            cal = plant["growing_calendar"]
            for region in REGIONS:
                assert region in cal, f"{plant['common_name']} missing region: {region}"

    def test_growing_calendar_valid_activities(self, plants_data):
        for plant in plants_data:
            for region, activities in plant["growing_calendar"].items():
                for activity in activities:
                    assert activity in VALID_ACTIVITIES, (
                        f"{plant['common_name']} / {region} has invalid activity: {activity}"
                    )

    def test_growing_calendar_month_ranges(self, plants_data):
        for plant in plants_data:
            for region, activities in plant["growing_calendar"].items():
                for activity, months in activities.items():
                    assert isinstance(months, list) and len(months) == 2, (
                        f"{plant['common_name']} / {region} / {activity}: expected [start, end], got {months}"
                    )
                    assert 1 <= months[0] <= 12, (
                        f"{plant['common_name']} / {region} / {activity}: month_start {months[0]} out of range"
                    )
                    assert 1 <= months[1] <= 12, (
                        f"{plant['common_name']} / {region} / {activity}: month_end {months[1]} out of range"
                    )

    def test_spacing_has_required_keys(self, plants_data):
        for plant in plants_data:
            sp = plant["spacing_cm"]
            assert "between_plants" in sp, f"{plant['common_name']} spacing missing between_plants"
            assert "between_rows" in sp, f"{plant['common_name']} spacing missing between_rows"

    def test_pests_and_diseases_are_lists(self, plants_data):
        for plant in plants_data:
            assert isinstance(plant["common_pests"], list), f"{plant['common_name']} common_pests is not a list"
            assert isinstance(plant["common_diseases"], list), f"{plant['common_name']} common_diseases is not a list"


# ---------------------------------------------------------------------------
# Model conversion tests
# ---------------------------------------------------------------------------


class TestModelConversion:
    """Test that JSON entries convert correctly to SQLAlchemy models."""

    def test_plant_dict_to_model(self, plants_data):
        plant = _plant_dict_to_model(plants_data[0])
        assert plant.common_name == plants_data[0]["common_name"]
        assert plant.category == plants_data[0]["category"]
        assert plant.id is not None

    def test_calendar_entries_created(self, plants_data):
        plant_id = uuid.uuid4()
        entries = _calendar_entries(plant_id, plants_data[0])
        assert len(entries) > 0
        for entry in entries:
            assert entry.plant_spec_id == plant_id
            assert entry.uk_region in REGIONS
            assert entry.activity in VALID_ACTIVITIES
            assert 1 <= entry.month_start <= 12
            assert 1 <= entry.month_end <= 12


# ---------------------------------------------------------------------------
# Seed function test (mocked DB)
# ---------------------------------------------------------------------------


class TestSeedFunction:
    """Test the seed function with a mocked database session."""

    @pytest.mark.asyncio
    async def test_seed_creates_records(self):
        # Mock session: no existing plants
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []  # no existing plants
        mock_session.execute.return_value = mock_result

        counts = await seed(mock_session)

        assert counts["plants_created"] == 50
        assert counts["calendars_created"] > 0
        mock_session.add.assert_called()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self, plants_data):
        # Mock session: all plants already exist
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(p["common_name"],) for p in plants_data]
        mock_session.execute.return_value = mock_result

        counts = await seed(mock_session)

        assert counts["plants_created"] == 0
        assert counts["calendars_created"] == 0
        mock_session.add.assert_not_called()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_seed_skips_existing_adds_new(self, plants_data):
        # First 10 already exist
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(p["common_name"],) for p in plants_data[:10]]
        mock_session.execute.return_value = mock_result

        counts = await seed(mock_session)

        assert counts["plants_created"] == 40
        assert counts["calendars_created"] > 0
