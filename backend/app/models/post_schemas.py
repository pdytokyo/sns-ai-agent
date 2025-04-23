from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PostBase(BaseModel):
    caption: str
    media_url: Optional[str] = None
    engagement_count: Optional[int] = None
    posted: bool = False
    post_error: Optional[str] = None
    platform: str = "instagram"

class PostCreate(PostBase):
    client_id: int
    video_id: Optional[int] = None

class PostRead(PostBase):
    id: int
    client_id: int
    video_id: Optional[int] = None
    created_at: datetime
