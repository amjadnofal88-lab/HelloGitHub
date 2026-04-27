from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db

router = APIRouter()


@router.get("/")
def list_claims(db: Session = Depends(get_db)):
    return []


@router.get("/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    return {"id": claim_id}
