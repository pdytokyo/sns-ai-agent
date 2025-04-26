from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import json

from . import Base

if TYPE_CHECKING:
    from .user import User
    from .video import Video
    from .post import Post
    from .script import Script
    from .report import Report
    from .job_log import JobLog

class Client(SQLModel, Base, table=True):
    __tablename__ = "clients"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    industry: str
    target_audience: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    user: Optional["User"] = Relationship(back_populates="clients")
    videos: List["Video"] = Relationship(back_populates="client")
    posts: List["Post"] = Relationship(back_populates="client")
    scripts: List["Script"] = Relationship(back_populates="client")
    reports: List["Report"] = Relationship(back_populates="client")
    job_logs: List["JobLog"] = Relationship(back_populates="client")
    
    @classmethod
    def validate_target_audience(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return {}
        return v or {}
