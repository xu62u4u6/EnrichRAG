"""Centralized logging configuration for EnrichRAG."""

import sys

from loguru import logger

# Remove default handler
logger.remove()


def setup_logging(level: str = "INFO") -> None:
    """Configure loguru with the given log level."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=(
            "<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | "
            "<cyan>{name}</cyan> - <level>{message}</level>"
        ),
    )


# Auto-setup on import; can be reconfigured later via setup_logging()
def _auto_setup() -> None:
    import os

    setup_logging(os.getenv("LOG_LEVEL", "INFO"))


_auto_setup()

__all__ = ["logger", "setup_logging"]
