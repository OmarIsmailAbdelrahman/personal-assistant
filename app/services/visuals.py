import os
import uuid
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy.orm import Session
from app.db.models import Media
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_chart(user_text: str, conversation_id: str, db: Session) -> str:
    """
    Generate a chart/visualization based on user request.
    
    For MVP, this generates a simple demo chart.
    In production, this would analyze the request and generate appropriate visualizations.
    
    Returns: media_id as string
    """
    # Ensure media directory exists
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    
    # Generate a unique ID for this media
    media_id = uuid.uuid4()
    filename = f"{media_id}.png"
    filepath = os.path.join(settings.MEDIA_DIR, filename)
    
    logger.info(
        "Generating chart",
        conversation_id=conversation_id,
        media_id=str(media_id)
    )
    
    try:
        # Generate a simple demo chart
        # In production, this would parse user_text and generate appropriate visualization
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Sample data
        x = np.linspace(0, 10, 100)
        y1 = np.sin(x)
        y2 = np.cos(x)
        
        ax.plot(x, y1, label='Sin(x)', linewidth=2)
        ax.plot(x, y2, label='Cos(x)', linewidth=2)
        ax.set_xlabel('X axis')
        ax.set_ylabel('Y axis')
        ax.set_title('Sample Visualization')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Save the figure
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(
            "Chart generated successfully",
            conversation_id=conversation_id,
            media_id=str(media_id),
            filepath=filepath
        )
        
        # Create Media record
        media = Media(
            id=media_id,
            conversation_id=conversation_id,
            media_type="image/png",
            storage_path=filepath
        )
        db.add(media)
        db.flush()
        
        return str(media_id)
        
    except Exception as e:
        logger.error(
            "Failed to generate chart",
            conversation_id=conversation_id,
            error=str(e)
        )
        raise
