from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ReportBase(BaseModel):
    title: str
    data: Dict[str, Any]
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

class ReportCreate(ReportBase):
    client_id: int

class ReportRead(ReportBase):
    id: int
    client_id: int
    created_at: datetime
