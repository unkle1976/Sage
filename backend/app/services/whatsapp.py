import httpx


class WhatsAppService:
    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, token: str, phone_number_id: str):
        self._token = token
        self._phone_number_id = phone_number_id
        self._client = httpx.AsyncClient(
            base_url=f"{self.BASE_URL}/{phone_number_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def send_text(self, to: str, text: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def send_buttons(self, to: str, body: str, buttons: list[dict]) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons[:3]  # WhatsApp max 3 buttons
                    ]
                },
            },
        }
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def send_list(self, to: str, body: str, button_text: str, sections: list[dict]) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body},
                "action": {"button": button_text, "sections": sections},
            },
        }
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def download_media(self, media_id: str) -> bytes:
        """Download media file from WhatsApp (for photo analysis)."""
        url_response = await self._client.get(
            f"{self.BASE_URL}/{media_id}",
            headers={"Authorization": f"Bearer {self._token}"},
        )
        url_response.raise_for_status()
        media_url = url_response.json()["url"]
        media_response = await self._client.get(
            media_url, headers={"Authorization": f"Bearer {self._token}"}
        )
        media_response.raise_for_status()
        return media_response.content

    async def close(self):
        await self._client.aclose()
