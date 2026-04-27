from sqlalchemy.orm import Session

from db.models import Policy


def get_policies(db: Session):
    return db.query(Policy).all()


def get_policy(db: Session, policy_id: int):
    return db.query(Policy).filter(Policy.id == policy_id).first()
