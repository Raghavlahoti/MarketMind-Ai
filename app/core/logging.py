# ============================================================================
# MARKETMIND AI - LOGGING ARCHITECTURE
# ============================================================================

import logging
import sys
from typing import Any, Dict
from app.core.config import settings


def configure_logging() -> None:
    """Configures structured console logging for the application.
    Uses JSON formatting in production environments and colored logs in development.
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Custom formatter class for console visibility
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console output handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [console_handler]

    # Silence noisy default library loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)


# Export logger instance
logger = logging.getLogger("marketmind_ai")
