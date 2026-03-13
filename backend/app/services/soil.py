import httpx


class SoilService:
    """Lookup soil type from BGS data. Results cached permanently (soil doesn't change)."""

    BASE_URL = "https://mapapps2.bgs.ac.uk/ukso/api"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)
        self._cache: dict[str, dict] = {}  # Simple in-memory cache

    async def get_soil_type(self, latitude: float, longitude: float) -> dict:
        """Get soil type for a location from BGS."""
        cache_key = f"{latitude:.4f},{longitude:.4f}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # BGS API endpoint for soil type at a point
        try:
            response = await self._client.get(
                f"{self.BASE_URL}/properties",
                params={"lat": latitude, "lon": longitude},
            )
            if response.status_code == 200:
                data = response.json()
                result = self._parse_soil_data(data)
            else:
                result = self._default_soil()
        except httpx.HTTPError:
            result = self._default_soil()

        self._cache[cache_key] = result
        return result

    def _parse_soil_data(self, data: dict) -> dict:
        """Extract useful soil info from BGS response."""
        # BGS API response format varies; extract what we can
        properties = data.get("properties", {})
        return {
            "soil_type": properties.get("soilType", "unknown"),
            "texture": properties.get("texture", "unknown"),
            "drainage": properties.get("drainage", "unknown"),
            "ph_range": properties.get("phRange", "unknown"),
            "source": "bgs",
        }

    def _default_soil(self) -> dict:
        return {
            "soil_type": "unknown",
            "texture": "unknown",
            "drainage": "unknown",
            "ph_range": "unknown",
            "source": "default",
        }

    async def close(self):
        await self._client.aclose()
