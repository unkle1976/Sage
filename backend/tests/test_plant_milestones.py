from app.data.plant_milestones import PLANT_MILESTONES


def test_milestones_have_required_keys():
    for plant_name, data in PLANT_MILESTONES.items():
        assert "milestones" in data, f"{plant_name} missing milestones"
        assert "facts" in data, f"{plant_name} missing facts"
        for m in data["milestones"]:
            assert "day" in m, f"{plant_name} milestone missing day"
            assert "stage" in m, f"{plant_name} milestone missing stage"
            assert "check_in" in m, f"{plant_name} milestone missing check_in"


def test_milestones_are_ordered_by_day():
    for plant_name, data in PLANT_MILESTONES.items():
        days = [m["day"] for m in data["milestones"]]
        assert days == sorted(days), f"{plant_name} milestones not in day order"


def test_weather_gates_are_valid():
    for plant_name, data in PLANT_MILESTONES.items():
        for m in data["milestones"]:
            if "weather_gate" in m:
                gate = m["weather_gate"]
                assert any(k in gate for k in ["min_temp", "max_temp", "no_frost"]), \
                    f"{plant_name} milestone has invalid weather_gate"


def test_minimum_plant_coverage():
    assert len(PLANT_MILESTONES) >= 15


def test_each_plant_has_sow_method():
    for plant_name, data in PLANT_MILESTONES.items():
        assert "sow_method" in data, f"{plant_name} missing sow_method"
        assert data["sow_method"] in ("indoor", "outdoor", "either"), \
            f"{plant_name} has invalid sow_method: {data['sow_method']}"


def test_each_plant_has_at_least_3_facts():
    for plant_name, data in PLANT_MILESTONES.items():
        assert len(data["facts"]) >= 3, f"{plant_name} needs at least 3 facts"


def test_each_plant_has_at_least_4_milestones():
    for plant_name, data in PLANT_MILESTONES.items():
        assert len(data["milestones"]) >= 4, f"{plant_name} needs at least 4 milestones"
