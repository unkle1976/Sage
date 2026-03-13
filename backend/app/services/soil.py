import httpx


# Regional soil defaults based on UK geology — used when BGS API is unavailable.
# These are generalised but better than "unknown" for gardening advice.
UK_SOIL_DEFAULTS: dict[str, dict] = {
    # Lincolnshire coast / Humber area — silty clay, alluvial
    "north east lincolnshire": {"soil_type": "silty clay", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "7.0-8.0"},
    "north lincolnshire": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "7.0-8.0"},
    "east lindsey": {"soil_type": "silty loam", "texture": "medium", "drainage": "moderate", "ph_range": "6.5-7.5"},
    "west lindsey": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "poor-moderate", "ph_range": "7.0-8.0"},
    # London
    "city of london": {"soil_type": "london clay", "texture": "heavy", "drainage": "poor", "ph_range": "7.0-8.0"},
    "westminster": {"soil_type": "london clay", "texture": "heavy", "drainage": "poor", "ph_range": "7.0-8.0"},
    "camden": {"soil_type": "london clay", "texture": "heavy", "drainage": "poor", "ph_range": "7.0-8.0"},
    # South West
    "bristol": {"soil_type": "clay loam", "texture": "medium", "drainage": "moderate", "ph_range": "6.5-7.5"},
    "bath and north east somerset": {"soil_type": "clay loam", "texture": "medium", "drainage": "moderate", "ph_range": "6.5-7.5"},
    "devon": {"soil_type": "loam", "texture": "medium", "drainage": "well-drained", "ph_range": "5.5-6.5"},
    "cornwall": {"soil_type": "loam", "texture": "medium-light", "drainage": "well-drained", "ph_range": "5.5-6.5"},
    # Midlands
    "birmingham": {"soil_type": "clay", "texture": "heavy", "drainage": "poor", "ph_range": "6.5-7.5"},
    "warwickshire": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.5-7.5"},
    # East
    "norfolk": {"soil_type": "sandy loam", "texture": "light", "drainage": "well-drained", "ph_range": "6.0-7.0"},
    "suffolk": {"soil_type": "sandy loam", "texture": "light-medium", "drainage": "well-drained", "ph_range": "6.5-7.5"},
    "cambridgeshire": {"soil_type": "chalky clay", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "7.5-8.5"},
    # North
    "leeds": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.0-7.0"},
    "sheffield": {"soil_type": "clay", "texture": "heavy", "drainage": "poor-moderate", "ph_range": "5.5-6.5"},
    "manchester": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.0-7.0"},
    # Scotland
    "edinburgh": {"soil_type": "clay loam", "texture": "medium", "drainage": "moderate", "ph_range": "6.0-7.0"},
    "glasgow": {"soil_type": "clay", "texture": "heavy", "drainage": "poor", "ph_range": "5.5-6.5"},
    # Wales
    "cardiff": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.5-7.5"},
    "swansea": {"soil_type": "loam", "texture": "medium", "drainage": "moderate", "ph_range": "5.5-6.5"},
}

# Broader regional fallbacks (by postcodes.io region)
UK_REGION_SOIL_DEFAULTS: dict[str, dict] = {
    "south east": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "7.0-8.0"},
    "south west": {"soil_type": "loam", "texture": "medium", "drainage": "well-drained", "ph_range": "6.0-7.0"},
    "london": {"soil_type": "london clay", "texture": "heavy", "drainage": "poor", "ph_range": "7.0-8.0"},
    "east of england": {"soil_type": "sandy loam", "texture": "light-medium", "drainage": "well-drained", "ph_range": "6.5-7.5"},
    "west midlands": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.5-7.5"},
    "east midlands": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.5-7.5"},
    "yorkshire and the humber": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.0-7.0"},
    "north west": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "poor-moderate", "ph_range": "5.5-6.5"},
    "north east": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "moderate", "ph_range": "6.0-7.0"},
    "scotland": {"soil_type": "loam", "texture": "medium", "drainage": "moderate", "ph_range": "5.5-6.5"},
    "wales": {"soil_type": "loam", "texture": "medium", "drainage": "moderate", "ph_range": "5.5-6.5"},
    "northern ireland": {"soil_type": "clay loam", "texture": "medium-heavy", "drainage": "poor-moderate", "ph_range": "5.5-6.5"},
}


class SoilService:
    """Lookup soil type — tries BGS API first, falls back to regional defaults."""

    BASE_URL = "https://mapapps2.bgs.ac.uk/ukso/api"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=10.0)
        self._cache: dict[str, dict] = {}

    async def get_soil_type(
        self,
        latitude: float,
        longitude: float,
        admin_district: str | None = None,
        region: str | None = None,
    ) -> dict:
        """Get soil type for a location. Tries BGS API, then regional lookup."""
        cache_key = f"{latitude:.4f},{longitude:.4f}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try BGS API first
        result = await self._try_bgs(latitude, longitude)

        # Fall back to admin district lookup
        if result["source"] == "default" and admin_district:
            district_result = UK_SOIL_DEFAULTS.get(admin_district.lower())
            if district_result:
                result = {**district_result, "source": f"regional ({admin_district})"}

        # Fall back to broader region
        if result["source"] == "default" and region:
            region_result = UK_REGION_SOIL_DEFAULTS.get(region.lower())
            if region_result:
                result = {**region_result, "source": f"regional ({region})"}

        self._cache[cache_key] = result
        return result

    async def _try_bgs(self, latitude: float, longitude: float) -> dict:
        """Attempt BGS API lookup. Returns default on any failure."""
        try:
            response = await self._client.get(
                f"{self.BASE_URL}/properties",
                params={"lat": latitude, "lon": longitude},
            )
            if response.status_code == 200:
                data = response.json()
                properties = data.get("properties", {})
                soil_type = properties.get("soilType")
                if soil_type and soil_type != "unknown":
                    return {
                        "soil_type": soil_type,
                        "texture": properties.get("texture", "unknown"),
                        "drainage": properties.get("drainage", "unknown"),
                        "ph_range": properties.get("phRange", "unknown"),
                        "source": "bgs",
                    }
        except (httpx.HTTPError, Exception):
            pass
        return self._default_soil()

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
