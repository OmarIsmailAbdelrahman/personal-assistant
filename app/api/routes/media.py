from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
import os
from app.db.session import get_db
from app.db.models import User, Media
from app.core.security import get_current_user
from app.core.logging import get_logger

router = APIRouter(prefix="/v1/media", tags=["media"])
logger = get_logger(__name__)


@router.get("/{media_id}")
async def get_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve a media file"""
    # Get the media record
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Verify the media belongs to the user's conversation
    if media.conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this media"
        )
    
    # Check if file exists
    if not os.path.exists(media.storage_path):
        logger.error(
            "Media file not found on disk",
            media_id=str(media_id),
            storage_path=media.storage_path
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found"
        )
    
    logger.info(
        "Media file served",
        media_id=str(media_id),
        user_id=str(current_user.id)
    )
    
    return FileResponse(
        path=media.storage_path,
        media_type=media.media_type,
        filename=f"{media_id}.png"
    )
