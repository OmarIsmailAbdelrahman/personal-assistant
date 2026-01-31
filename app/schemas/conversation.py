from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation information"""
    id: UUID
    user_id: UUID
    title: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
