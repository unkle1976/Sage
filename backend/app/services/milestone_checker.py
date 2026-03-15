from __future__ import annotations
from datetime import date, timedelta


class MilestoneChecker:
    def get_due_milestones(
        self,
        plants: list,
        today: date,
        weather: dict | None = None,
    ) -> list[dict]:
        due = []
        for plant in plants:
            spec = getattr(plant, "plant_spec", None)
            if not spec or not spec.growth_milestones or not plant.planting_date:
                continue

            milestones = spec.growth_milestones
            idx = plant.next_milestone_index or 0

            if idx >= len(milestones):
                continue

            milestone = milestones[idx]
            milestone_date = plant.planting_date + timedelta(days=milestone["day"])

            if milestone_date > today:
                continue

            delayed = False
            gate = milestone.get("weather_gate")
            if gate and weather:
                if gate.get("min_temp") and weather.get("temp_min_c", 99) < gate["min_temp"]:
                    delayed = True
                if gate.get("no_frost") and weather.get("frost"):
                    delayed = True

            due.append({
                "plant": plant,
                "plant_name": spec.common_name,
                "variety": plant.variety,
                "stage": milestone["stage"],
                "check_in": milestone["check_in"],
                "milestone_index": idx,
                "delayed": delayed,
                "days_since_planting": (today - plant.planting_date).days,
            })

        return due
