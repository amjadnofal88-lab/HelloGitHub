from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402 — must come after load_dotenv

from .router import router

app = FastAPI(title="WhatsApp Notification API")
app.include_router(router)
