import uuid
from datetime import date

from app.models.weather_log import WeatherLog


def test_weather_log_fields():
    log = WeatherLog(
        id=uuid.uuid4(),
        postcode_outward="DN35",
        date=date(2026, 3, 14),
        temp_max_c=14.5,
        temp_min_c=3.2,
        rainfall_mm=2.1,
        wind_max_kmh=25.0,
        sunshine_hours=6.5,
        frost=False,
    )
    assert log.postcode_outward == "DN35"
    assert log.temp_max_c == 14.5
    assert log.frost is False
