from __future__ import annotations
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime

Base = declarative_base()

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True)
    event = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AgentRegistry(Base):
    __tablename__ = 'agent_registry'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    role = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
