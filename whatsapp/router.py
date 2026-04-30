from fastapi import APIRouter

from .services import WhatsAppService

router = APIRouter()


@router.post("/whatsapp/send")
async def send_whatsapp(phone: str, message: str):
    wa = WhatsAppService()
    return await wa.send_message(phone, message)
