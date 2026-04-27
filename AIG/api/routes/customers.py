from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db

router = APIRouter()


@router.get("/")
def list_customers(db: Session = Depends(get_db)):
    return []


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return {"id": customer_id}
