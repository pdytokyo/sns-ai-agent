from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime

from . import Base
from .client import Client

class Script(SQLModel, Base, table=True):
    __tablename__ = "scripts"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    keywords: Optional[str] = None
    hook: Optional[str] = None
    target_platform: str = "instagram"
    client_id: int = Field(default=None, foreign_key="clients.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship(back_populates="scripts")
