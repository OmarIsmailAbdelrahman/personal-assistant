import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import AgentRun, Message, Media
from app.core.config import settings
from app.core.logging import get_logger
from app.services.visuals import generate_chart
from app.services.integration import send_to_external_system

# Gemini API
import google.generativeai as genai

logger = get_logger(__name__)


def execute_agent_run(run_id: str, db: Session):
    """
    Execute an agent run.
    
    This is the main agent execution logic. Currently uses Gemini API directly,
    but is structured to easily integrate LangGraph in the future.
    """
    # Load the agent run
    agent_run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not agent_run:
        logger.error("Agent run not found", run_id=run_id)
        return
    
    # Update status to running
    agent_run.status = "running"
    agent_run.started_at = datetime.utcnow()
    db.commit()
    
    logger.info(
        "Agent run started",
        run_id=run_id,
        conversation_id=str(agent_run.conversation_id)
    )
    
    try:
        # Load conversation history
        messages = db.query(Message).filter(
            Message.conversation_id == agent_run.conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        # Get the trigger message
        trigger_message = db.query(Message).filter(
            Message.id == agent_run.trigger_message_id
        ).first()
        
        user_text = trigger_message.content_json.get("text", "")
        
        # Check if user wants a visualization
        generate_visual = "plot:" in user_text.lower() or "chart:" in user_text.lower()
        
        # Build conversation context for the agent
        conversation_context = []
        for msg in messages:
            if msg.sender == "user":
                conversation_context.append({
                    "role": "user",
                    "parts": [msg.content_json.get("text", "")]
                })
            elif msg.sender == "assistant":
                conversation_context.append({
                    "role": "model",
                    "parts": [msg.content_json.get("text", "")]
                })
        
        # Run the agent (Gemini API for now - LangGraph can replace this later)
        response_text = _run_gemini_agent(conversation_context, user_text)
        
        # Store assistant text response
        assistant_message = Message(
            conversation_id=agent_run.conversation_id,
            sender="assistant",
            content_json={
                "type": "text",
                "text": response_text
            }
        )
        db.add(assistant_message)
        db.flush()
        
        logger.info(
            "Assistant message created",
            run_id=run_id,
            message_id=str(assistant_message.id)
        )
        
        # Generate visualization if requested
        media_id = None
        if generate_visual:
            try:
                media_id = generate_chart(
                    user_text=user_text,
                    conversation_id=str(agent_run.conversation_id),
                    db=db
                )
                
                if media_id:
                    # Create image message
                    image_message = Message(
                        conversation_id=agent_run.conversation_id,
                        sender="assistant",
                        content_json={
                            "type": "image",
                            "url": f"/v1/media/{media_id}",
                            "caption": "Generated visualization"
                        }
                    )
                    db.add(image_message)
                    db.flush()
                    
                    logger.info(
                        "Visualization generated and message created",
                        run_id=run_id,
                        media_id=str(media_id)
                    )
            except Exception as e:
                logger.error(
                    "Failed to generate visualization",
                    run_id=run_id,
                    error=str(e)
                )
        
        # Call external integration
        integration_payload = {
            "user_id": str(agent_run.conversation.user_id),
            "conversation_id": str(agent_run.conversation_id),
            "run_id": run_id,
            "final_text": response_text,
            "created_at": datetime.utcnow().isoformat(),
            "has_visualization": media_id is not None
        }
        
        send_to_external_system(run_id, integration_payload, db)
        
        # Mark run as succeeded
        agent_run.status = "succeeded"
        agent_run.finished_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            "Agent run completed successfully",
            run_id=run_id,
            conversation_id=str(agent_run.conversation_id)
        )
        
    except Exception as e:
        # Mark run as failed
        agent_run.status = "failed"
        agent_run.finished_at = datetime.utcnow()
        agent_run.last_error = str(e)
        db.commit()
        
        logger.error(
            "Agent run failed",
            run_id=run_id,
            error=str(e)
        )
        raise


def _run_gemini_agent(conversation_context: list, user_text: str) -> str:
    """
    Run the Gemini agent.
    
    This function is a placeholder that uses Gemini API directly.
    In the future, this can be replaced with LangGraph execution
    while keeping the same interface.
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini API key not set, using echo response")
        return f"Echo: {user_text}"
    
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Start a chat with history
        chat = model.start_chat(history=conversation_context[:-1] if len(conversation_context) > 1 else [])
        
        # Send the latest message
        response = chat.send_message(user_text)
        
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini API call failed: {str(e)}")
        # Fallback to echo
        return f"I received your message: {user_text}"
