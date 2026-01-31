from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class RunStatusResponse(BaseModel):
    """Agent run status information"""
    id: UUID
    conversation_id: UUID
    trigger_message_id: UUID
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
