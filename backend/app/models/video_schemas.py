from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VideoBase(BaseModel):
    title: str
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    processed: bool = False
    processing_error: Optional[str] = None

class VideoCreate(VideoBase):
    client_id: int

class VideoRead(VideoBase):
    id: int
    client_id: int
    created_at: datetime
