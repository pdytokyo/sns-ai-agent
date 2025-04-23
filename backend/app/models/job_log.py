from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime

from backend.app.models import Base
from backend.app.models.user import User
from backend.app.models.client import Client

class JobLog(SQLModel, Base, table=True):
    __tablename__ = "job_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str
    status: str
    error_message: Optional[str] = None
    client_id: Optional[int] = Field(default=None, foreign_key="clients.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship(back_populates="job_logs")
    user: Optional[User] = Relationship(back_populates="job_logs")
