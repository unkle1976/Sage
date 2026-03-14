from app.services.proactive import ProactiveMessageBuilder


def test_build_context_summary_combines_plants():
    plants = [
        {"variety": "Tomato", "growth_stage": "flowering", "planting_date": "2026-03-01"},
        {"variety": "Courgette", "growth_stage": "established", "planting_date": "2026-04-15"},
        {"variety": "Radish", "growth_stage": "ready_to_harvest", "planting_date": "2026-02-20"},
    ]
    summary = ProactiveMessageBuilder.build_plant_summary(plants)
    assert "Tomato" in summary
    assert "Courgette" in summary
    assert "Radish" in summary


def test_build_trigger_context():
    triggers = {
        "weather_alerts": [{"type": "frost", "min_temp": -1}],
        "care_due": [{"plant": "Courgette", "action": "feed", "product": "potash"}],
        "growth_updates": [{"plant": "Radish", "expected_stage": "ready_to_harvest"}],
    }
    context = ProactiveMessageBuilder.build_trigger_context(triggers)
    assert "frost" in context.lower()
    assert "courgette" in context.lower()
    assert "radish" in context.lower()
