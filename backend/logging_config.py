"""
Centralized logging configuration for ScholarSource backend.

This module sets up logging once and provides a simple get_logger() function
that all backend modules can use.
"""
import logging
from pathlib import Path
from typing import Optional

# Global flag to ensure we only configure once
_logging_configured = False


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = "cache.log",
    log_dir: Optional[Path] = None
) -> None:
    """
    Configure logging for the entire application.

    This should be called once at application startup. Subsequent calls are ignored.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Name of log file (None to disable file logging)
        log_dir: Directory for log files (defaults to /logs in project root)
    """
    global _logging_configured

    if _logging_configured:
        return  # Already configured

    # Determine log directory
    if log_dir is None:
        # Default to /logs directory in project root
        log_dir = Path(__file__).parent.parent / "logs"

    # Create log directory if it doesn't exist
    if log_file:
        log_dir.mkdir(exist_ok=True)

    # Create handlers
    handlers = []

    # Console handler (always included)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_dir / log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module.

    Usage:
        from backend.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance
    """
    # Auto-configure if not already done
    if not _logging_configured:
        configure_logging()

    return logging.getLogger(name)


# Convenience function for testing/debugging
def set_debug_mode():
    """Enable DEBUG level logging."""
    global _logging_configured
    _logging_configured = False  # Reset to allow reconfiguration
    configure_logging(log_level="DEBUG")
