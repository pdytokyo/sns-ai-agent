from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ScriptBase(BaseModel):
    title: Optional[str] = None
    content: str
    keywords: Optional[str] = None
    hook: Optional[str] = None
    target_platform: str = "instagram"

class ScriptCreate(ScriptBase):
    client_id: int

class ScriptRead(ScriptBase):
    id: int
    client_id: int
    created_at: datetime
