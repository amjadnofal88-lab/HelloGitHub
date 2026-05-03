import httpx
from fastapi import APIRouter, Depends, Request

from .services import WhatsAppService

router = APIRouter()


def get_whatsapp_service(request: Request) -> WhatsAppService:
    """Dependency that returns a WhatsAppService backed by the shared HTTP client."""
    return WhatsAppService(request.app.state.http_client)


@router.post("/whatsapp/send")
async def send_whatsapp(
    phone: str,
    message: str,
    wa: WhatsAppService = Depends(get_whatsapp_service),
):
    """Send a WhatsApp text message to the given phone number.

    Args:
        phone: Recipient phone in E.164 format (e.g. +15550001234).
        message: Plain-text message body.

    Returns:
        JSON response from the WhatsApp Cloud API, including the message ID.
    """
    return await wa.send_message(phone, message)
