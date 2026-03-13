import httpx


class PostcodeService:
    BASE_URL = "https://api.postcodes.io"

    def __init__(self):
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0)

    async def lookup(self, postcode: str) -> dict | None:
        """Look up a UK postcode, return lat/lng/region/admin_district or None."""
        response = await self._client.get(f"/postcodes/{postcode}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()["result"]
        return {
            "postcode": data["postcode"],
            "outward_code": data["outcode"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "region": data["region"],
            "admin_district": data["admin_district"],
        }

    async def validate(self, postcode: str) -> bool:
        """Check if a postcode is valid."""
        response = await self._client.get(f"/postcodes/{postcode}/validate")
        return response.json().get("result", False)

    async def close(self):
        await self._client.aclose()
