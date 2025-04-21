"""
Logging module for the LoRa GPS Tracker

This module sets up logging configuration for the tracker device
with structured logs and rotation.
"""
import os
import sys
from pathlib import Path
from loguru import logger

import config

# Create log directory if it doesn't exist
log_dir = os.path.dirname(config.LOG_FILE)
Path(log_dir).mkdir(parents=True, exist_ok=True)

# Remove default logger
logger.remove()

# Add console output
logger.add(
    sys.stdout,
    level=config.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>"
)

# Add file output with rotation
logger.add(
    config.LOG_FILE,
    rotation=config.LOG_ROTATION,
    retention=config.LOG_RETENTION,
    level=config.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    backtrace=True,
    diagnose=True
)

# Create logger for this module
log = logger.bind(module="logger")

log.debug("Logger initialized with level: {}", config.LOG_LEVEL)

# Create data directory if it doesn't exist
storage_dir = config.STORAGE_DIR
Path(storage_dir).mkdir(parents=True, exist_ok=True)
log.debug("Data directory created: {}", storage_dir)


def get_logger(module_name):
    """
    Get a logger instance for the specified module

    Args:
        module_name (str): Name of the module

    Returns:
        logger: Logger instance for the module
    """
    return logger.bind(module=module_name)
