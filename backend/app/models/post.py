from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from . import Base
from .client import Client

if TYPE_CHECKING:
    from .video import Video

class Post(SQLModel, Base, table=True):
    __tablename__ = "posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    caption: str
    media_url: Optional[str] = None
    engagement_count: Optional[int] = None
    posted: bool = False
    post_error: Optional[str] = None
    platform: str = "instagram"
    client_id: int = Field(default=None, foreign_key="clients.id")
    video_id: Optional[int] = Field(default=None, foreign_key="videos.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship(back_populates="posts")
    video: Optional["Video"] = Relationship(back_populates="posts")
