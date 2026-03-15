"""Proactive message building — gathers triggers and builds context for Claude."""


class ProactiveMessageBuilder:

    @staticmethod
    def build_plant_summary(plants: list[dict]) -> str:
        if not plants:
            return "No active plants."
        parts = []
        for p in plants:
            variety = p.get("variety", "Unknown")
            stage = p.get("growth_stage", "unknown").replace("_", " ")
            parts.append(f"{variety} ({stage})")
        return "Active plants: " + ", ".join(parts)

    @staticmethod
    def build_trigger_context(triggers: dict) -> str:
        lines = []
        for alert in triggers.get("weather_alerts", []):
            alert_type = alert.get("type", "weather")
            if alert_type == "frost":
                lines.append(f"URGENT: Frost warning — minimum temperature {alert.get('min_temp')}°C")
            elif alert_type == "heatwave":
                lines.append(f"URGENT: Heatwave — temperatures reaching {alert.get('max_temp')}°C")
            else:
                lines.append(f"Weather alert: {alert_type}")
        for care in triggers.get("care_due", []):
            plant = care.get("plant", "plants")
            action = care.get("action", "care")
            product = care.get("product")
            if product:
                lines.append(f"Care due: {plant} needs {action} (suggest {product})")
            else:
                lines.append(f"Care due: {plant} needs {action}")
        for update in triggers.get("growth_updates", []):
            plant = update.get("plant", "plant")
            expected = update.get("expected_stage", "next stage").replace("_", " ")
            lines.append(f"Growth check: {plant} should be at {expected} stage by now")
        if not lines:
            lines.append("General check-in — no specific triggers, just being friendly")
        return "\n".join(lines)

    @staticmethod
    def build_milestone_context(milestones: list[dict]) -> str:
        if not milestones:
            return ""
        lines = ["MILESTONE CHECK-INS DUE:"]
        for m in milestones:
            name = m["plant_name"]
            if m.get("variety"):
                name += f" ({m['variety']})"
            status = "DELAYED by weather" if m["delayed"] else f"Day {m['days_since_planting']}"
            lines.append(f"- {name}: {m['stage']} ({status}) — {m['check_in']}")
        return "\n".join(lines)

    @staticmethod
    def build_system_instruction(trigger_context: str, plant_summary: str, user_name: str, experience_level: str) -> str:
        return f"""You are Sage, a friendly gardening mate. Generate a proactive WhatsApp message.

RULES:
- ONE message covering the whole garden — NEVER separate messages per plant
- Maximum 2-3 sentences. It's WhatsApp, not an essay
- Ask at most ONE question (or none — not every message needs a reply)
- Vary your tone: sometimes practical, sometimes curious, sometimes celebratory
- Don't be robotic or template-y — sound like a mate
- Use UK English
- Tailor complexity to experience level: {experience_level}

USER: {user_name}
{plant_summary}

TRIGGERS:
{trigger_context}

Write the message now. Just the message text, nothing else."""
