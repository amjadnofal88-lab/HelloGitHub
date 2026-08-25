# models.py
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String)
    api_key = Column(String, unique=True)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"))

    type = Column(String)
    status = Column(String)

    payload = Column(Text)
    result = Column(Text)
    error = Column(Text)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
