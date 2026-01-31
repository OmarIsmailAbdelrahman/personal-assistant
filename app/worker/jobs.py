from app.db.session import SessionLocal
from app.services.agent_runner import execute_agent_run
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_agent_job(run_id: str):
    """
    RQ job function to execute an agent run.
    
    This is the entry point for the background worker.
    """
    logger.info("Agent job started", run_id=run_id)
    
    db = SessionLocal()
    try:
        execute_agent_run(run_id, db)
    finally:
        db.close()
    
    logger.info("Agent job completed", run_id=run_id)
