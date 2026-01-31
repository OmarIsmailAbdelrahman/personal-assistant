import sys
from redis import Redis
from rq import Worker, Queue, Connection
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":
    logger.info("Starting RQ worker")
    
    # Connect to Redis
    redis_conn = Redis.from_url(settings.REDIS_URL)
    
    # Create worker
    with Connection(redis_conn):
        worker = Worker([Queue("default")])
        logger.info("RQ worker listening on 'default' queue")
        worker.work()
