"""
Structured logging utility for Krishi-Sarthi.
"""

import logging
import sys
from app.config import get_settings


def get_logger(name: str) -> logging.Logger:
    """Create a structured logger with console output."""
    settings = get_settings()
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger
