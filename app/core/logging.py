import logging
import sys
import json
from datetime import datetime
from typing import Any, Optional


class StructuredLogger:
    """Structured JSON logger with correlation fields"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler with JSON formatting
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)
    
    def _log(
        self,
        level: str,
        message: str,
        conversation_id: Optional[str] = None,
        run_id: Optional[str] = None,
        message_id: Optional[str] = None,
        **kwargs: Any
    ):
        """Log structured message with correlation fields"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
        }
        
        if conversation_id:
            log_data["conversation_id"] = conversation_id
        if run_id:
            log_data["run_id"] = run_id
        if message_id:
            log_data["message_id"] = message_id
            
        # Add any additional fields
        log_data.update(kwargs)
        
        # Log as JSON
        log_str = json.dumps(log_data)
        
        if level == "INFO":
            self.logger.info(log_str)
        elif level == "ERROR":
            self.logger.error(log_str)
        elif level == "WARNING":
            self.logger.warning(log_str)
        elif level == "DEBUG":
            self.logger.debug(log_str)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
