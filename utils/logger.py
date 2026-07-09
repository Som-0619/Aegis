"""
Standardized logging utility for the Project Health Reporting Agent.
Configures console logging and rotating file logs under outputs/logs/.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# Default log directory in outputs/logs relative to the project root
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "outputs",
    "logs"
)

def setup_logging(log_level: int = logging.INFO) -> None:
    """
    Sets up the global logging configurations with console and file handlers.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)

    log_filepath = os.path.join(LOG_DIR, "project_health_agent.log")

    # Define standard format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    formatter = logging.Formatter(log_format)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate logging
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File Handler (10MB size limit, keeps up to 5 backups)
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.info(f"Logging initialized. Outputting logs to: {log_filepath}")

def get_logger(name: str) -> logging.Logger:
    """
    Helper function for components to retrieve a named logger.
    
    Args:
        name: Name of the logger (typically __name__).
    """
    return logging.getLogger(name)

# Auto-initialize logging on import
setup_logging()
