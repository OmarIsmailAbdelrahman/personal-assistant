from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.db.models import User, AgentRun
from app.core.security import get_current_user
from app.schemas.run import RunStatusResponse
from app.core.logging import get_logger

router = APIRouter(prefix="/v1/runs", tags=["runs"])
logger = get_logger(__name__)


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the status of an agent run"""
    # Get the run
    agent_run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    
    if not agent_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    # Verify the run belongs to the user's conversation
    if agent_run.conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this run"
        )
    
    logger.info(
        "Run status retrieved",
        run_id=str(run_id),
        status=agent_run.status,
        user_id=str(current_user.id)
    )
    
    return agent_run
