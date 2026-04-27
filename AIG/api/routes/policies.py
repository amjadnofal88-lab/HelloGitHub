from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db

router = APIRouter()


@router.get("/")
def list_policies(db: Session = Depends(get_db)):
    return []


@router.get("/{policy_id}")
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    return {"id": policy_id}
