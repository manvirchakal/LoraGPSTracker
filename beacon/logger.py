"""
Logging configuration for the beacon component

This module sets up the logging system for the beacon component.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import config

# Ensure log directory exists
os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)

# Create logger
logger = logging.getLogger("beacon")
logger.setLevel(getattr(logging, config.LOG_LEVEL))

# Determine log file rotation settings
if "MB" in config.LOG_ROTATION:
    max_bytes = int(config.LOG_ROTATION.split()[0]) * 1024 * 1024
else:
    max_bytes = 10 * 1024 * 1024  # Default 10MB

# Create handlers
console_handler = logging.StreamHandler(sys.stdout)
file_handler = RotatingFileHandler(
    config.LOG_FILE,
    maxBytes=max_bytes,
    backupCount=5
)

# Create formatters
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(log_format, date_format)

# Add formatters to handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def get_logger():
    """
    Returns the configured logger instance.
    
    Returns:
        logging.Logger: The configured logger instance
    """
    return logger

def log_startup_info():
    """Logs system information at startup"""
    logger.info("=" * 50)
    logger.info(f"Beacon application starting at {datetime.now().isoformat()}")
    logger.info(f"Beacon ID: {config.BEACON_ID}")
    logger.info(f"Beacon Type: {config.BEACON_TYPE}")
    logger.info(f"LoRa Port: {config.LORA_PORT}")
    logger.info(f"LoRa Frequency: {config.LORA_FREQUENCY} MHz")
    logger.info(f"GPS Port: {config.GPS_PORT}")
    logger.info(f"Log Level: {config.LOG_LEVEL}")
    logger.info("=" * 50)

def log_error_with_context(error, context=None):
    """
    Logs an error with additional context information
    
    Args:
        error (Exception): The exception to log
        context (dict, optional): Additional contextual information
    """
    if context is None:
        context = {}
    
    error_message = f"ERROR: {str(error)}"
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        error_message += f" | Context: {context_str}"
    
    logger.error(error_message, exc_info=True)
