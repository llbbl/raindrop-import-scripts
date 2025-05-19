"""
Logging functionality for import scripts.

This module provides functions for setting up logging with consistent formatting
and support for both console and file output.
"""

import logging
import sys
from typing import Optional

logger = None


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Initialize logger and log format.

    Parameters
    ----------
    log_file : str, optional
        Path to the log file. If provided, logs will be written to this file in addition to console output.
    """
    global logger
    log_format = "%(asctime)s | %(levelname)8s | %(message)s"
    handlers = [logging.StreamHandler(stream=sys.stdout)]

    # Add file handler if log file is provided
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
            print(f"Logging to file: {log_file}")
        except Exception as e:
            print(f"Warning: Could not set up logging to file {log_file}: {e}")

    logging.basicConfig(handlers=handlers, level=logging.INFO, format=log_format)
    logger = logging.getLogger(__name__)


def get_logger() -> logging.Logger:
    """
    Get the configured logger instance.

    Returns
    -------
    logging.Logger
        The configured logger instance.

    Raises
    ------
    RuntimeError
        If setup_logging has not been called before this function.
    """
    if logger is None:
        raise RuntimeError("Logger not initialized. Call setup_logging() first.")
    return logger