"""
Centralized logging configuration for ScholarSource backend.

This module sets up logging once and provides a simple get_logger() function
that all backend modules can use.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Global flag to ensure we only configure once
_logging_configured = False


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: Optional[Path] = None,
    console_output: bool = True
) -> None:
    """
    Configure logging for the entire application.

    This should be called once at application startup. Subsequent calls are ignored.
    
    This configuration is designed to work alongside CrewAI's logging system.
    It preserves existing handlers and ensures CrewAI loggers are properly configured.

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
        # Default to ./logs directory in project root (relative to backend/)
        project_root = Path(__file__).parent.parent
        log_dir = project_root / "logs"

    # Create log directory if it doesn't exist
    if log_file:
        log_dir.mkdir(exist_ok=True, parents=True)
        # Verify directory was created
        if not log_dir.exists():
            raise OSError(f"Failed to create log directory: {log_dir}")

    # Configure logging ONLY for our application modules, not for CrewAI
    # CrewAI uses print() statements for verbose output, not logging
    # We don't want to interfere with CrewAI's output
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Only configure if root logger has no handlers (to avoid interfering with CrewAI)
    # If handlers already exist, don't add more
    if not root_logger.handlers:
        # Create handlers only for our application logging
        handlers = []

        # Console handler for our application logs (only if requested)
        # Use stdout explicitly so Railway doesn't classify as errors
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            handlers.append(console_handler)

        # File handler (optional) for our application logs
        if log_file:
            file_handler = logging.FileHandler(log_dir / log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            handlers.append(file_handler)

        # Configure root logger level
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Add our handlers to the root logger
        for handler in handlers:
            root_logger.addHandler(handler)
    
    # Don't configure CrewAI loggers - let CrewAI handle its own output
    # CrewAI's verbose=True uses print() statements, not logging
    
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

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
    # DON'T auto-configure - let the application explicitly configure logging
    # Auto-configuring interferes with CrewAI's print() statements
    # If logging isn't configured, Python's default logging will be used (which is fine)
    # return logging.getLogger(name)
    
    # Actually, let's just return the logger without configuring
    # The application should explicitly call configure_logging() if needed
    return logging.getLogger(name)


# Convenience function for testing/debugging
def set_debug_mode():
    """Enable DEBUG level logging."""
    global _logging_configured
    _logging_configured = False  # Reset to allow reconfiguration
    configure_logging(log_level="DEBUG")

