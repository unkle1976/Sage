from app.services.proactive import ProactiveMessageBuilder


def test_build_milestone_context():
    milestones = [
        {"plant_name": "Tomato", "variety": "Gardener's Delight", "stage": "sprouting",
         "check_in": "Should be sprouting by now", "delayed": False, "days_since_planting": 10},
    ]
    ctx = ProactiveMessageBuilder.build_milestone_context(milestones)
    assert "Tomato" in ctx
    assert "sprouting" in ctx
    assert "Gardener's Delight" in ctx


def test_build_milestone_context_delayed():
    milestones = [
        {"plant_name": "Tomato", "stage": "hardening_off", "variety": None,
         "check_in": "Put outside", "delayed": True, "days_since_planting": 42},
    ]
    ctx = ProactiveMessageBuilder.build_milestone_context(milestones)
    assert "delay" in ctx.lower() or "DELAY" in ctx


def test_build_milestone_context_empty():
    ctx = ProactiveMessageBuilder.build_milestone_context([])
    assert ctx == ""


def test_build_milestone_context_multiple():
    milestones = [
        {"plant_name": "Tomato", "variety": None, "stage": "sprouting",
         "check_in": "Check for sprouts", "delayed": False, "days_since_planting": 10},
        {"plant_name": "Lettuce", "variety": "Little Gem", "stage": "harvest",
         "check_in": "Ready to pick", "delayed": False, "days_since_planting": 60},
    ]
    ctx = ProactiveMessageBuilder.build_milestone_context(milestones)
    assert "Tomato" in ctx
    assert "Lettuce" in ctx
