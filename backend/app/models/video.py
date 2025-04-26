from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from . import Base
from .client import Client

if TYPE_CHECKING:
    from backend.app.models.post import Post

class Video(SQLModel, Base, table=True):
    __tablename__ = "videos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    processed: bool = False
    processing_error: Optional[str] = None
    client_id: int = Field(default=None, foreign_key="clients.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship(back_populates="videos")
    posts: List["Post"] = Relationship(back_populates="video")
