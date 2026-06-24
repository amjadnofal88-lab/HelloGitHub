import httpx

from .config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_API_BASE_URL


class WhatsAppService:
    """Sends messages via the Meta WhatsApp Cloud API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def send_message(self, phone: str, message: str) -> dict:
        """Send a text message to the given phone number.

        Args:
            phone: Recipient phone number in E.164 format (e.g. +15550001234).
            message: Plain-text message body.

        Returns:
            The JSON response from the WhatsApp Cloud API.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status code.
        """
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message},
        }
        response = await self._client.post(
            WHATSAPP_API_BASE_URL, json=payload, headers=headers
        )
        response.raise_for_status()
        return response.json()
