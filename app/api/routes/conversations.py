from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User, Conversation
from app.core.security import get_current_user
from app.schemas.conversation import CreateConversationRequest, ConversationResponse
from app.core.logging import get_logger

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])
logger = get_logger(__name__)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    conversation = Conversation(
        user_id=current_user.id,
        title=request.title
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    logger.info(
        "Conversation created",
        user_id=str(current_user.id),
        conversation_id=str(conversation.id)
    )
    
    return conversation
