import re

import httpx


class PostcodeService:
    BASE_URL = "https://api.postcodes.io"

    def __init__(self):
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0)

    @staticmethod
    def normalise(raw: str) -> str:
        """Normalise messy postcode input from WhatsApp.

        Handles: lowercase, missing spaces, extra whitespace, inner spaces in outcodes.
        """
        text = raw.strip().upper()
        # Remove all spaces for analysis
        compact = text.replace(" ", "")

        # Full UK postcode pattern: A9A 9AA, A9 9AA, A99 9AA, AA9 9AA, AA99 9AA, AA9A 9AA
        # Inward part is always 3 chars: 9AA
        if re.match(r"^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$", compact):
            # Insert space before last 3 characters
            return f"{compact[:-3]} {compact[-3:]}"

        # Otherwise treat as outward code — just return uppercased, spaces removed
        return compact

    async def lookup(self, raw_postcode: str) -> dict | None:
        """Look up a UK postcode or outward code.

        Tries full postcode first, then falls back to outcode endpoint.
        Returns lat/lng/region/admin_district or None.
        """
        postcode = self.normalise(raw_postcode)

        # Try full postcode lookup
        result = await self._try_full_postcode(postcode)
        if result:
            return result

        # Fall back to outcode lookup (handles "DN35", "B44", etc.)
        outcode = postcode.split()[0] if " " in postcode else postcode
        return await self._try_outcode(outcode)

    async def _try_full_postcode(self, postcode: str) -> dict | None:
        """Try the /postcodes/ endpoint for a full postcode."""
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
            "region": data.get("region"),
            "admin_district": data.get("admin_district"),
        }

    async def _try_outcode(self, outcode: str) -> dict | None:
        """Try the /outcodes/ endpoint for an outward code like DN35 or B44."""
        response = await self._client.get(f"/outcodes/{outcode}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()["result"]

        # Outcode endpoint returns admin_district as a list — take first
        admin_district = data.get("admin_district", [])
        if isinstance(admin_district, list):
            admin_district = admin_district[0] if admin_district else None

        return {
            "postcode": None,
            "outward_code": data.get("outcode", outcode),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "region": None,  # Outcode endpoint doesn't return region
            "admin_district": admin_district,
        }

    async def validate(self, postcode: str) -> bool:
        """Check if a postcode is valid."""
        response = await self._client.get(f"/postcodes/{postcode}/validate")
        return response.json().get("result", False)

    async def close(self):
        await self._client.aclose()
