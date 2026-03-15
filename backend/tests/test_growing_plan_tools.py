from app.agents.tools import TOOLS


def test_manage_growing_plan_tool_exists():
    names = [t["name"] for t in TOOLS]
    assert "manage_growing_plan" in names


def test_advance_milestone_tool_exists():
    names = [t["name"] for t in TOOLS]
    assert "advance_milestone" in names


def test_manage_growing_plan_schema():
    tool = next(t for t in TOOLS if t["name"] == "manage_growing_plan")
    props = tool["input_schema"]["properties"]
    assert "action" in props
    assert "plant_name" in props


def test_advance_milestone_schema():
    tool = next(t for t in TOOLS if t["name"] == "advance_milestone")
    props = tool["input_schema"]["properties"]
    assert "plant_name" in props
    assert "user_confirmed" in props
