from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid

from . import Base

if TYPE_CHECKING:
    from backend.app.models.client import Client
    from backend.app.models.job_log import JobLog
    from backend.app.models.token import Token

class User(SQLModel, Base, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    clients: List["Client"] = Relationship(back_populates="user")
    job_logs: List["JobLog"] = Relationship(back_populates="user")
    tokens: List["Token"] = Relationship(back_populates="user")
