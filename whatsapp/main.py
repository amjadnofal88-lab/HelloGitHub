from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from .config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
from .router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [
        name
        for name, value in [
            ("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_NUMBER_ID),
            ("WHATSAPP_ACCESS_TOKEN", WHATSAPP_ACCESS_TOKEN),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="WhatsApp Notification API", lifespan=lifespan)
app.include_router(router)
