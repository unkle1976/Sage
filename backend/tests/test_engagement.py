from datetime import time

from app.services.engagement import EngagementService


def test_sporadic_chance_active_user():
    chance = EngagementService.calculate_sporadic_chance(days_since_contact=1, current_month=6)
    assert 0 < chance < 0.10

def test_sporadic_chance_dormant_user():
    chance = EngagementService.calculate_sporadic_chance(days_since_contact=15, current_month=5)
    assert chance >= 0.5

def test_sporadic_chance_winter_low():
    chance = EngagementService.calculate_sporadic_chance(days_since_contact=7, current_month=12)
    summer_chance = EngagementService.calculate_sporadic_chance(days_since_contact=7, current_month=6)
    assert chance < summer_chance

def test_is_quiet_hours():
    assert EngagementService.is_quiet_hours(current_time=time(23, 0), quiet_start=time(22, 0), quiet_end=time(7, 0)) is True
    assert EngagementService.is_quiet_hours(current_time=time(12, 0), quiet_start=time(22, 0), quiet_end=time(7, 0)) is False

def test_is_quiet_hours_none():
    assert EngagementService.is_quiet_hours(current_time=time(3, 0), quiet_start=None, quiet_end=None) is False
