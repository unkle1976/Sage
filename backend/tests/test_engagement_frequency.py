from app.services.engagement import EngagementService


def test_frequency_normal_at_zero_unanswered():
    assert EngagementService.get_frequency_for_unanswered(0) == "normal"


def test_frequency_normal_at_one_unanswered():
    assert EngagementService.get_frequency_for_unanswered(1) == "normal"


def test_frequency_normal_at_two_unanswered():
    assert EngagementService.get_frequency_for_unanswered(2) == "normal"


def test_frequency_reduced_at_three():
    assert EngagementService.get_frequency_for_unanswered(3) == "reduced"


def test_frequency_minimal_at_four_plus():
    assert EngagementService.get_frequency_for_unanswered(4) == "minimal"
    assert EngagementService.get_frequency_for_unanswered(10) == "minimal"


def test_should_nudge_at_two():
    assert EngagementService.should_nudge(2) is True


def test_should_not_nudge_at_one():
    assert EngagementService.should_nudge(1) is False


def test_should_not_nudge_at_three():
    assert EngagementService.should_nudge(3) is False


def test_min_days_normal():
    assert EngagementService.min_days_between("normal") == 3


def test_min_days_reduced():
    assert EngagementService.min_days_between("reduced") == 7


def test_min_days_minimal():
    assert EngagementService.min_days_between("minimal") == 14
