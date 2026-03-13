import httpx


class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1"

    def __init__(self):
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=15.0)

    async def get_forecast(self, latitude: float, longitude: float) -> dict:
        """Get 7-day forecast for a location."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "hourly": "temperature_2m,precipitation,relative_humidity_2m",
            "timezone": "Europe/London",
            "forecast_days": 7,
        }
        response = await self._client.get("/forecast", params=params)
        response.raise_for_status()
        return response.json()

    async def check_frost_risk(self, latitude: float, longitude: float, hours: int = 72) -> dict:
        """Check frost risk for the next N hours."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m",
            "timezone": "Europe/London",
            "forecast_hours": hours,
        }
        response = await self._client.get("/forecast", params=params)
        response.raise_for_status()
        data = response.json()

        temps = data.get("hourly", {}).get("temperature_2m", [])
        times = data.get("hourly", {}).get("time", [])

        frost_hours = []
        for i, temp in enumerate(temps):
            if temp is not None and temp <= 2.0:
                frost_hours.append({"time": times[i], "temperature": temp})

        return {
            "frost_risk": len(frost_hours) > 0,
            "frost_hours": frost_hours,
            "min_temperature": min(temps) if temps else None,
        }

    async def get_watering_guidance(self, latitude: float, longitude: float) -> dict:
        """Determine if watering is needed based on recent and forecast rainfall."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "precipitation_sum,temperature_2m_max",
            "timezone": "Europe/London",
            "past_days": 3,
            "forecast_days": 3,
        }
        response = await self._client.get("/forecast", params=params)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        precip = daily.get("precipitation_sum", [])
        temps = daily.get("temperature_2m_max", [])

        recent_rain = sum(p for p in precip[:3] if p is not None)
        forecast_rain = sum(p for p in precip[3:] if p is not None)
        max_temp = max(temps) if temps else 20

        needs_water = recent_rain < 5.0 and forecast_rain < 5.0 and max_temp > 18
        return {
            "needs_watering": needs_water,
            "recent_rainfall_mm": round(recent_rain, 1),
            "forecast_rainfall_mm": round(forecast_rain, 1),
            "max_temperature": max_temp,
        }

    async def close(self):
        await self._client.aclose()
