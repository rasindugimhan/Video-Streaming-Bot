import logging
import os
from config import LOG_DIR, LOG_LEVEL, LOG_FORMAT

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name):
    """Get a configured logger instance"""
    logger = logging.getLogger(name)
    
    # Only add handlers if they don't exist
    if not logger.handlers:
        # Set log level
        logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # File handler
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, f'{name}.log'))
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
