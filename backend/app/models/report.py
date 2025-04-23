from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from typing import Optional, Dict, Any
from datetime import datetime

from backend.app.models import Base
from backend.app.models.client import Client

class Report(SQLModel, Base, table=True):
    __tablename__ = "reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    data: Dict[str, Any] = Field(sa_column=Column(JSON))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    client_id: int = Field(default=None, foreign_key="clients.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship(back_populates="reports")
