import time
from typing import Dict, Any
from sqlalchemy.orm import Session
import httpx
from app.db.models import IntegrationDelivery, AgentRun
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_to_external_system(run_id: str, payload: Dict[str, Any], db: Session):
    """
    Send data to external system with retries.
    
    Uses exponential backoff: 1s, 2s, 4s for 3 attempts total.
    Records delivery status in integration_deliveries table.
    """
    # Check if integration is enabled
    if not settings.INTEGRATION_URL:
        logger.info(
            "Integration disabled (INTEGRATION_URL not set)",
            run_id=run_id
        )
        return
    
    # Create integration delivery record
    delivery = IntegrationDelivery(
        run_id=run_id,
        status="pending",
        attempts=0
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    
    logger.info(
        "Starting integration delivery",
        run_id=run_id,
        delivery_id=str(delivery.id),
        url=settings.INTEGRATION_URL
    )
    
    # Retry configuration
    max_attempts = 3
    backoff_delays = [1, 2, 4]  # seconds
    
    for attempt in range(max_attempts):
        delivery.attempts = attempt + 1
        db.commit()
        
        try:
            logger.info(
                f"Integration delivery attempt {attempt + 1}/{max_attempts}",
                run_id=run_id,
                delivery_id=str(delivery.id)
            )
            
            # Make HTTP POST request
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    settings.INTEGRATION_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Check if successful
                if response.status_code in [200, 201, 202]:
                    delivery.status = "succeeded"
                    db.commit()
                    
                    logger.info(
                        "Integration delivery succeeded",
                        run_id=run_id,
                        delivery_id=str(delivery.id),
                        status_code=response.status_code,
                        attempts=delivery.attempts
                    )
                    return
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    delivery.last_error = error_msg
                    db.commit()
                    
                    logger.warning(
                        "Integration delivery failed with bad status code",
                        run_id=run_id,
                        delivery_id=str(delivery.id),
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                    
        except Exception as e:
            error_msg = str(e)
            delivery.last_error = error_msg
            db.commit()
            
            logger.error(
                "Integration delivery failed with exception",
                run_id=run_id,
                delivery_id=str(delivery.id),
                error=error_msg,
                attempt=attempt + 1
            )
        
        # Wait before retry (except on last attempt)
        if attempt < max_attempts - 1:
            delay = backoff_delays[attempt]
            logger.info(
                f"Waiting {delay}s before retry",
                run_id=run_id,
                delivery_id=str(delivery.id)
            )
            time.sleep(delay)
    
    # All attempts failed
    delivery.status = "failed"
    db.commit()
    
    logger.error(
        "Integration delivery failed after all attempts",
        run_id=run_id,
        delivery_id=str(delivery.id),
        attempts=delivery.attempts
    )
