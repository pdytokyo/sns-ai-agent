from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ClientBase(BaseModel):
    name: str
    industry: Optional[str] = None
    target_audience: Optional[Dict[str, Any]] = None

class ClientCreate(ClientBase):
    user_id: Optional[int] = None

class ClientRead(ClientBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
