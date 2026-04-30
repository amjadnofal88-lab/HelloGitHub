from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_auth import router as auth_router
from app.api.routes_cases import router as cases_router
from app.api.routes_events import router as events_router
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown (nothing needed for now)


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(events_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
