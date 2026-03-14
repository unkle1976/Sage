"""Proactive engagement logic — determines when and whether Sage should reach out."""

import random
from datetime import time as time_type


class EngagementService:
    SEASON_MULTIPLIERS = {
        1: 0.3, 2: 0.3,
        3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5,
        7: 1.0, 8: 1.0, 9: 1.0,
        10: 0.7, 11: 0.3, 12: 0.3,
    }

    @staticmethod
    def calculate_sporadic_chance(days_since_contact: int, current_month: int) -> float:
        if days_since_contact <= 2:
            base_chance = 0.05
        elif days_since_contact <= 5:
            base_chance = 0.15
        elif days_since_contact <= 14:
            base_chance = 0.30
        else:
            base_chance = 0.50

        multiplier = EngagementService.SEASON_MULTIPLIERS.get(current_month, 1.0)
        return base_chance * multiplier

    @staticmethod
    def should_send_sporadic(days_since_contact: int, current_month: int) -> bool:
        chance = EngagementService.calculate_sporadic_chance(days_since_contact, current_month)
        return random.random() < chance

    @staticmethod
    def is_quiet_hours(current_time: time_type, quiet_start: time_type | None, quiet_end: time_type | None) -> bool:
        if quiet_start is None or quiet_end is None:
            return False
        if quiet_start <= quiet_end:
            return quiet_start <= current_time <= quiet_end
        else:
            return current_time >= quiet_start or current_time <= quiet_end
