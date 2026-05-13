"""
Logging functionality for import scripts.

This module provides functions for setting up logging with consistent formatting
and support for both console and file output.
"""

import logging
import sys

logger = None


def setup_logging(log_file: str | None = None) -> None:
    """
    Initialize logger and log format.

    Parameters
    ----------
    log_file : str, optional
        Path to the log file. If provided, logs will be written to this file in addition to console output.
    """
    global logger
    log_format = "%(asctime)s | %(levelname)8s | %(message)s"
    formatter = logging.Formatter(log_format)

    # Create console handler
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)

    # Initialize handlers list
    handlers: list[logging.Handler] = [console_handler]

    # Add file handler if log file is provided
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode="a")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
            print(f"Logging to file: {log_file}")
        except Exception as e:
            print(f"Warning: Could not set up logging to file {log_file}: {e}")

    # Configure root logger
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Configure module logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add handlers to module logger
    for handler in handlers:
        logger.addHandler(handler)


def get_logger() -> logging.Logger:
    """
    Get the configured logger instance.

    If ``setup_logging()`` has not been called yet, fall back to a default
    logger configured with a basic handler. This avoids forcing every caller
    (notably converter classes constructed without an explicit logger) to
    sequence ``setup_logging()`` before instantiation, while still letting
    ``setup_logging()`` reconfigure handlers when invoked.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """
    global logger
    if logger is None:
        # Default fallback: emit to stderr at INFO. setup_logging() may later
        # replace handlers; we just need a usable logger right now.
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler(stream=sys.stderr)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)8s | %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
