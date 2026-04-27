from pydantic import BaseModel


class PolicyBase(BaseModel):
    policy_number: str
    customer_id: int


class PolicyCreate(PolicyBase):
    pass


class PolicyRead(PolicyBase):
    id: int

    class Config:
        from_attributes = True
