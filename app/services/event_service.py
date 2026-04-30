from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        case_id: str,
        event_type: str,
        payload: str | None = None,
    ) -> Event:
        event = Event(case_id=case_id, event_type=event_type, payload=payload)
        self.db.add(event)
        await self.db.flush()
        return event

    async def get(self, event_id: str) -> Event | None:
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def list_for_case(
        self, case_id: str, skip: int = 0, limit: int = 50
    ) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .where(Event.case_id == case_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_pending(self, limit: int = 100) -> list[Event]:
        """Return events that have not yet been processed successfully."""
        result = await self.db.execute(
            select(Event).where(Event.status == "pending").limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processed(self, event: Event) -> Event:
        event.status = "processed"
        await self.db.flush()
        return event

    async def mark_failed(self, event: Event) -> Event:
        event.retry_count += 1
        event.status = "failed"
        await self.db.flush()
        return event
