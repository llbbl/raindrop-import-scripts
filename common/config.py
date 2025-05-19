"""
Configuration handling for import scripts.

This module provides functionality to load and apply configuration settings
from a configuration file. The configuration file can specify default values
for command-line arguments and other settings.
"""

import argparse
import os
import yaml
from typing import Any, Dict, Optional

from common.logging import get_logger, setup_logging
import logging


def _get_or_setup_logger() -> logging.Logger:
    """
    Get the logger, initializing it if necessary.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """
    try:
        return get_logger()
    except RuntimeError:
        # Logger not initialized, set it up with default settings
        setup_logging()
        return get_logger()


def get_config_file_path() -> str:
    """
    Get the path to the configuration file.

    The configuration file is searched for in the following locations:
    1. The current directory (./raindrop_import.yaml)
    2. The user's home directory (~/.raindrop_import.yaml)

    Returns
    -------
    str
        The path to the configuration file, or an empty string if not found.
    """
    # Check current directory
    if os.path.exists("raindrop_import.yaml"):
        return "raindrop_import.yaml"

    # Check home directory
    home_config = os.path.expanduser("~/.raindrop_import.yaml")
    if os.path.exists(home_config):
        return home_config

    return ""


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Parameters
    ----------
    config_file : str, optional
        Path to the configuration file. If not provided, the default locations
        will be searched.

    Returns
    -------
    Dict[str, Any]
        The loaded configuration, or an empty dictionary if the file doesn't exist
        or can't be parsed.
    """
    logger = _get_or_setup_logger()

    if not config_file:
        config_file = get_config_file_path()

    if not config_file:
        logger.debug("No configuration file found")
        return {}

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            logger.warning(f"Invalid configuration format in {config_file}")
            return {}

        logger.info(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        logger.warning(f"Failed to load configuration from {config_file}: {e}")
        return {}


def apply_config_to_args(args: argparse.Namespace, config: Dict[str, Any]) -> argparse.Namespace:
    """
    Apply configuration settings to command-line arguments.

    This function applies configuration settings to command-line arguments,
    but only for arguments that weren't explicitly provided on the command line.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    config : Dict[str, Any]
        Configuration settings.

    Returns
    -------
    argparse.Namespace
        Updated arguments with configuration settings applied.
    """
    logger = _get_or_setup_logger()

    # Get the source-specific configuration
    source_config = config.get(args.source, {})

    # Apply global configuration
    global_config = config.get("global", {})
    for key, value in global_config.items():
        if not hasattr(args, key) or getattr(args, key) is None:
            setattr(args, key, value)
            logger.debug(f"Applied global configuration: {key}={value}")

    # Apply source-specific configuration (overrides global)
    for key, value in source_config.items():
        # Source-specific config overrides global config even if already set from global
        if hasattr(args, key) and key in global_config and getattr(args, key) == global_config[key]:
            setattr(args, key, value)
            logger.debug(f"Overrode global configuration with {args.source} configuration: {key}={value}")
        # Apply source-specific config if not explicitly set on command line
        elif not hasattr(args, key) or getattr(args, key) is None:
            setattr(args, key, value)
            logger.debug(f"Applied {args.source} configuration: {key}={value}")

    return args
