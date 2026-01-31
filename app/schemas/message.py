from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class PostMessageRequest(BaseModel):
    """Request to post a new message"""
    text: str
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Message information"""
    id: UUID
    conversation_id: UUID
    sender: str
    content_json: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostMessageResponse(BaseModel):
    """Response after posting a message"""
    message_id: UUID
    run_id: UUID
    status: str
