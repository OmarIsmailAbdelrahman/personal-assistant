from redis import Redis
from rq import Queue
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Redis connection
redis_conn = Redis.from_url(settings.REDIS_URL)

# RQ Queue
job_queue = Queue("default", connection=redis_conn)


def enqueue_agent_run(run_id: str):
    """Enqueue an agent run job to RQ"""
    from app.worker.jobs import run_agent_job
    
    job = job_queue.enqueue(
        run_agent_job,
        run_id,
        job_timeout="10m",
        result_ttl=3600,  # Keep result for 1 hour
        failure_ttl=86400  # Keep failed jobs for 24 hours
    )
    
    logger.info(
        "Agent run job enqueued",
        run_id=run_id,
        job_id=job.id
    )
    
    return job.id
