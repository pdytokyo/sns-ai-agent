from sqlmodel import Field, SQLModel, Column, JSON
from typing import Optional, Dict, Any
from datetime import datetime

from . import Base

class CompetitorVideo(SQLModel, Base, table=True):
    __tablename__ = "competitor_videos"
    __table_args__ = {"extend_existing": True}
    
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str  # "tiktok" or "instagram"
    video_url: str
    engagement_rate: float
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    transcript: Optional[str] = None
    time_codes: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Store 3-second block timings
    char_counts: Dict[str, int] = Field(default={}, sa_column=Column(JSON))  # Store character counts per block
    created_at: datetime = Field(default_factory=datetime.utcnow)
