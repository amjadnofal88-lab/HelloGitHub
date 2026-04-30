from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])


class CaseCreate(BaseModel):
    tenant_id: str
    owner_id: str
    title: str
    description: str | None = None


class CaseStatusUpdate(BaseModel):
    status: str


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_case(payload: CaseCreate, db: AsyncSession = Depends(get_db)):
    svc = CaseService(db)
    case = await svc.create(
        tenant_id=payload.tenant_id,
        owner_id=payload.owner_id,
        title=payload.title,
        description=payload.description,
    )
    return {"id": case.id, "title": case.title, "status": case.status}


@router.get("/")
async def list_cases(
    tenant_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    svc = CaseService(db)
    cases = await svc.list(tenant_id=tenant_id, skip=skip, limit=limit)
    return [{"id": c.id, "title": c.title, "status": c.status} for c in cases]


@router.get("/{case_id}")
async def get_case(case_id: str, tenant_id: str, db: AsyncSession = Depends(get_db)):
    svc = CaseService(db)
    case = await svc.get(case_id, tenant_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"id": case.id, "title": case.title, "status": case.status, "description": case.description}


@router.patch("/{case_id}/status")
async def update_case_status(
    case_id: str,
    tenant_id: str,
    payload: CaseStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = CaseService(db)
    try:
        case = await svc.update_status(case_id, tenant_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"id": case.id, "status": case.status}


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str, tenant_id: str, db: AsyncSession = Depends(get_db)):
    svc = CaseService(db)
    try:
        await svc.delete(case_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
