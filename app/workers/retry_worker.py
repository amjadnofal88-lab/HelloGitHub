"""Background worker that retries failed events."""
import asyncio
import logging

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.services.event_service import EventService

logger = logging.getLogger(__name__)


async def process_event(event: Event, svc: EventService) -> None:
    """Attempt to process a single pending/failed event."""
    try:
        # TODO: plug in real processing logic per event_type
        logger.info("Processing event %s (type=%s)", event.id, event.event_type)
        await svc.mark_processed(event)
        logger.info("Event %s marked as processed", event.id)
    except Exception as exc:
        logger.warning("Event %s failed (attempt %d): %s", event.id, event.retry_count + 1, exc)
        await svc.mark_failed(event)


async def retry_loop() -> None:
    """Main loop: poll for pending/retryable events and process them."""
    logger.info("Retry worker started (interval=%ds)", settings.RETRY_INTERVAL_SECONDS)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                svc = EventService(db)
                events = await svc.list_pending(limit=100)
                retryable = [e for e in events if e.retry_count < settings.MAX_RETRY_ATTEMPTS]
                if retryable:
                    logger.info("Processing %d retryable event(s)", len(retryable))
                for event in retryable:
                    await process_event(event, svc)
                await db.commit()
        except Exception as exc:
            logger.error("Retry worker encountered an error: %s", exc, exc_info=True)

        await asyncio.sleep(settings.RETRY_INTERVAL_SECONDS)


def start() -> None:
    """Entry point for running the worker as a standalone process."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(retry_loop())


if __name__ == "__main__":
    start()
