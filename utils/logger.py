import logging
import sys
import os
from datetime import datetime

def setup_master_logger():
    """Setup master logger with file rotation"""
    logger = logging.getLogger('UPI_Bot')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-25s | %(lineno)-4d | %(message)s'
        )
        
        # Stream handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            'logs/bot.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = RotatingFileHandler(
            'logs/error.log',
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger

def log_security_event(logger, event, user_id, details):
    """Log security events"""
    logger.warning(f"🔒 SECURITY: {event} | User: {user_id} | Details: {details}")

def log_command_execution(logger, command, user_id, guild_id, success=True, error=None):
    """Log command execution"""
    status = "✅" if success else "❌"
    error_msg = f" | Error: {error}" if error else ""
    logger.info(f"{status} Command: {command} | User: {user_id} | Guild: {guild_id}{error_msg}")
  
