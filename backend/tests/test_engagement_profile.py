import uuid
from datetime import time

from app.models.engagement_profile import EngagementProfile


def test_engagement_profile_fields():
    profile = EngagementProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        preferred_time="morning",
        notification_level="normal",
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(7, 0),
    )
    assert profile.preferred_time == "morning"
    assert profile.notification_level == "normal"
    assert profile.quiet_hours_start == time(22, 0)


def test_engagement_profile_defaults():
    profile = EngagementProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )
    assert profile.preferred_time == "morning"
    assert profile.notification_level == "normal"
    assert profile.last_sage_initiated_at is None
    assert profile.last_user_message_at is None
