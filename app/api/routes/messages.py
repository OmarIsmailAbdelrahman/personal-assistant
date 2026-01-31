from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.db.session import get_db
from app.db.models import User, Conversation, Message, AgentRun
from app.core.security import get_current_user
from app.schemas.message import PostMessageRequest, MessageResponse, PostMessageResponse
from app.services.enqueue import enqueue_agent_run
from app.core.logging import get_logger

router = APIRouter(prefix="/v1/conversations", tags=["messages"])
logger = get_logger(__name__)


@router.post("/{conversation_id}/messages", response_model=PostMessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def post_message(
    conversation_id: UUID,
    request: PostMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post a user message and enqueue agent processing"""
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).filter(
        and_(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Create user message
    message = Message(
        conversation_id=conversation_id,
        sender="user",
        content_json={
            "type": "text",
            "text": request.text,
            "metadata": request.metadata or {}
        }
    )
    
    db.add(message)
    db.flush()  # Flush to get message.id
    
    # Create agent run
    agent_run = AgentRun(
        conversation_id=conversation_id,
        trigger_message_id=message.id,
        status="queued"
    )
    
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    
    logger.info(
        "User message posted, agent run queued",
        conversation_id=str(conversation_id),
        message_id=str(message.id),
        run_id=str(agent_run.id)
    )
    
    # Enqueue background job
    enqueue_agent_run(str(agent_run.id))
    
    return PostMessageResponse(
        message_id=message.id,
        run_id=agent_run.id,
        status="queued"
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    after_id: Optional[UUID] = Query(None, description="Get messages after this ID"),
    since: Optional[datetime] = Query(None, description="Get messages since this timestamp"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Poll messages in a conversation"""
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).filter(
        and_(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Build query
    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    
    # Apply filters
    if after_id:
        # Get the timestamp of the after_id message
        after_message = db.query(Message).filter(Message.id == after_id).first()
        if after_message:
            query = query.filter(Message.created_at > after_message.created_at)
    
    if since:
        query = query.filter(Message.created_at > since)
    
    # Order and limit
    messages = query.order_by(Message.created_at.asc()).limit(limit).all()
    
    logger.info(
        f"Retrieved {len(messages)} messages",
        conversation_id=str(conversation_id),
        user_id=str(current_user.id)
    )
    
    return messages
