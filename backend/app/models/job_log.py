from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime

from . import Base
from .user import User
from .client import Client

class JobLog(SQLModel, Base, table=True):
    __tablename__ = "job_logs"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str
    status: str
    error_message: Optional[str] = None
    client_id: Optional[int] = Field(default=None, foreign_key="clients.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship(back_populates="job_logs")
    user: Optional[User] = Relationship(back_populates="job_logs")
