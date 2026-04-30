from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402 — must come after load_dotenv

from .router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="WhatsApp Notification API", lifespan=lifespan)
app.include_router(router)
