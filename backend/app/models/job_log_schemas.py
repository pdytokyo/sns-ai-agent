from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobLogBase(BaseModel):
    job_type: str
    status: str
    error_message: Optional[str] = None
    client_id: Optional[int] = None
    user_id: Optional[int] = None

class JobLogCreate(JobLogBase):
    pass

class JobLogRead(JobLogBase):
    id: int
    created_at: datetime
