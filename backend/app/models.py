from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from pydantic import EmailStr, validator
import json

class UserBase(SQLModel):
    email: EmailStr
    username: str
    is_active: bool = True
    is_admin: bool = False

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    clients: List["Client"] = Relationship(back_populates="user")
    tokens: List["Token"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    created_at: datetime

class Token(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="tokens")

class TokenData(SQLModel):
    username: Optional[str] = None
    exp: Optional[datetime] = None

class ClientBase(SQLModel):
    name: str
    industry: Optional[str] = None
    target_audience: Optional[str] = Field(default=None, sa_column=Column(JSON))
    
    @validator("target_audience", pre=True)
    def validate_target_audience(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return {}
        return v or {}

class Client(ClientBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="clients")
    videos: List["Video"] = Relationship(back_populates="client")
    posts: List["Post"] = Relationship(back_populates="client")

class ClientCreate(ClientBase):
    pass

class ClientRead(ClientBase):
    id: int
    user_id: int
    created_at: datetime

class VideoBase(SQLModel):
    title: str
    file_path: str
    duration: Optional[float] = None
    processed: bool = False
    processing_error: Optional[str] = None

class Video(VideoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Client = Relationship(back_populates="videos")
    posts: List["Post"] = Relationship(back_populates="video")

class VideoCreate(VideoBase):
    client_id: int

class VideoRead(VideoBase):
    id: int
    client_id: int
    created_at: datetime

class ScriptBase(SQLModel):
    content: str
    keywords: Optional[str] = None
    hook: Optional[str] = None
    target_platform: str = "instagram"

class Script(ScriptBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Client = Relationship(back_populates="scripts")

class ScriptCreate(ScriptBase):
    client_id: int

class ScriptRead(ScriptBase):
    id: int
    client_id: int
    created_at: datetime

Client.scripts: List[Script] = Relationship(back_populates="client")

class PostBase(SQLModel):
    caption: str
    hashtags: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    posted: bool = False
    post_error: Optional[str] = None
    platform: str = "instagram"

class Post(PostBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    video_id: Optional[int] = Field(default=None, foreign_key="video.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Client = Relationship(back_populates="posts")
    video: Optional[Video] = Relationship(back_populates="posts")

class PostCreate(PostBase):
    client_id: int
    video_id: Optional[int] = None

class PostRead(PostBase):
    id: int
    client_id: int
    video_id: Optional[int]
    created_at: datetime

class ReportBase(SQLModel):
    report_type: str
    data: dict = Field(sa_column=Column(JSON))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

class Report(ReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Client = Relationship(back_populates="reports")

class ReportCreate(ReportBase):
    client_id: int

class ReportRead(ReportBase):
    id: int
    client_id: int
    created_at: datetime

Client.reports: List[Report] = Relationship(back_populates="client")

class JobLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str
    status: str
    error_message: Optional[str] = None
    client_id: Optional[int] = Field(default=None, foreign_key="client.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    client: Optional[Client] = Relationship()
    user: Optional[User] = Relationship()

class JobLogCreate(SQLModel):
    job_type: str
    status: str
    error_message: Optional[str] = None
    client_id: Optional[int] = None
    user_id: Optional[int] = None

class JobLogRead(SQLModel):
    id: int
    job_type: str
    status: str
    error_message: Optional[str] = None
    client_id: Optional[int] = None
    user_id: Optional[int] = None
    created_at: datetime
