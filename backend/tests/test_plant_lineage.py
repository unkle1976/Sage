import uuid

from app.models.plant import Plant


def test_plant_lineage_fields():
    parent_id = uuid.uuid4()
    season_id = uuid.uuid4()
    plant = Plant(
        id=uuid.uuid4(),
        garden_id=uuid.uuid4(),
        growing_season_id=season_id,
        parent_plant_id=parent_id,
        seed_source="saved_seed",
        final_outcome="success",
        yield_total_kg=4.2,
        season_notes="Great year for tomatoes",
    )
    assert plant.growing_season_id == season_id
    assert plant.parent_plant_id == parent_id
    assert plant.seed_source == "saved_seed"
    assert plant.final_outcome == "success"
    assert plant.yield_total_kg == 4.2
    assert plant.season_notes == "Great year for tomatoes"


def test_plant_lineage_defaults():
    plant = Plant(id=uuid.uuid4(), garden_id=uuid.uuid4())
    assert plant.growing_season_id is None
    assert plant.parent_plant_id is None
    assert plant.seed_source is None
    assert plant.final_outcome is None
    assert plant.yield_total_kg is None
    assert plant.season_notes is None
