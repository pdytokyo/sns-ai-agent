from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from . import Base

if TYPE_CHECKING:
    from backend.app.models.user import User

class Token(SQLModel, Base, table=True):
    __tablename__ = "tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: Optional["User"] = Relationship(back_populates="tokens")
