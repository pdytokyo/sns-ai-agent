from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import json

from backend.app.models import Base

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.video import Video
    from backend.app.models.post import Post
    from backend.app.models.script import Script
    from backend.app.models.report import Report
    from backend.app.models.job_log import JobLog

class Client(SQLModel, Base, table=True):
    __tablename__ = "clients"
    
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
