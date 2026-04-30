from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


class EventCreate(BaseModel):
    case_id: str
    event_type: str
    payload: str | None = None


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)):
    svc = EventService(db)
    event = await svc.create(
        case_id=payload.case_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    return {"id": event.id, "event_type": event.event_type, "status": event.status}


@router.get("/case/{case_id}")
async def list_events_for_case(
    case_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    svc = EventService(db)
    events = await svc.list_for_case(case_id=case_id, skip=skip, limit=limit)
    return [
        {"id": e.id, "event_type": e.event_type, "status": e.status, "retry_count": e.retry_count}
        for e in events
    ]


@router.get("/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    svc = EventService(db)
    event = await svc.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return {
        "id": event.id,
        "case_id": event.case_id,
        "event_type": event.event_type,
        "payload": event.payload,
        "status": event.status,
        "retry_count": event.retry_count,
    }
