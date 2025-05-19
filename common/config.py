"""
Configuration handling for import scripts.

This module provides functionality to load and apply configuration settings
from a configuration file or environment variables. The configuration can specify 
default values for command-line arguments and other settings.

Configuration is loaded from the following sources, in order of precedence:
1. Command-line arguments
2. Configuration file (YAML)
3. Environment variables (.env file)
"""

import argparse
import os
import yaml
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    # If python-dotenv is not installed, provide a fallback
    def load_dotenv(dotenv_path=None):
        """Fallback function if python-dotenv is not installed."""
        return False

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


def get_env_file_path() -> str:
    """
    Get the path to the .env file.

    The .env file is searched for in the following locations:
    1. The current directory (./.env)
    2. The user's home directory (~/.raindrop_import.env)

    Returns
    -------
    str
        The path to the .env file, or an empty string if not found.
    """
    # Check current directory
    if os.path.exists(".env"):
        return ".env"

    # Check home directory
    home_env = os.path.expanduser("~/.raindrop_import.env")
    if os.path.exists(home_env):
        return home_env

    return ""


def load_env_vars() -> Dict[str, Any]:
    """
    Load environment variables from a .env file.

    Returns
    -------
    Dict[str, Any]
        A dictionary of environment variables loaded from the .env file.
    """
    logger = _get_or_setup_logger()

    # Get the path to the .env file
    env_file = get_env_file_path()

    if not env_file:
        logger.debug("No .env file found")
        return {}

    # Load the .env file
    try:
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")

        # Get all environment variables that start with RAINDROP_
        env_vars = {}
        for key, value in os.environ.items():
            if key.startswith("RAINDROP_"):
                # Convert RAINDROP_API_TOKEN to api_token
                config_key = key[9:].lower().replace("_", "-")

                # Convert string values to appropriate types
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
                    value = float(value)

                env_vars[config_key] = value

        return env_vars
    except Exception as e:
        logger.warning(f"Failed to load environment variables from {env_file}: {e}")
        return {}


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file and environment variables.

    Parameters
    ----------
    config_file : str, optional
        Path to the configuration file. If not provided, the default locations
        will be searched.

    Returns
    -------
    Dict[str, Any]
        The loaded configuration, or an empty dictionary if no configuration sources
        are available or can't be parsed.
    """
    logger = _get_or_setup_logger()
    config = {}

    # Load environment variables first (lowest precedence)
    env_vars = load_env_vars()
    if env_vars:
        # Create a structure similar to the YAML config
        for key, value in env_vars.items():
            parts = key.split("-")
            if len(parts) > 1 and parts[0] in ["global", "pocket", "evernote", "chrome", "firefox", "raindrop"]:
                # Handle source-specific config like RAINDROP_POCKET_INPUT_FILE
                source = parts[0]
                if source not in config:
                    config[source] = {}
                config[source]["-".join(parts[1:])] = value
            else:
                # Handle global config like RAINDROP_API_TOKEN
                if "global" not in config:
                    config["global"] = {}
                config["global"][key] = value
        logger.debug(f"Loaded {len(env_vars)} environment variables")

    # Load configuration file (overrides environment variables)
    if not config_file:
        config_file = get_config_file_path()

    if config_file:
        try:
            with open(config_file, "r") as f:
                file_config = yaml.safe_load(f)

            if not isinstance(file_config, dict):
                logger.warning(f"Invalid configuration format in {config_file}")
            else:
                # Merge file config with env vars (file config takes precedence)
                for section, values in file_config.items():
                    if section not in config:
                        config[section] = {}
                    config[section].update(values)
                logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.warning(f"Failed to load configuration from {config_file}: {e}")

    return config


def apply_config_to_args(args: argparse.Namespace, config: Dict[str, Any]) -> argparse.Namespace:
    """
    Apply configuration settings to command-line arguments.

    This function applies configuration settings to command-line arguments,
    but only for arguments that weren't explicitly provided on the command line.
    The order of precedence is:
    1. Command-line arguments
    2. Source-specific configuration
    3. Global configuration

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
        # Convert hyphens to underscores for compatibility with argparse
        arg_key = key.replace("-", "_")

        if not hasattr(args, arg_key) or getattr(args, arg_key) is None:
            setattr(args, arg_key, value)
            logger.debug(f"Applied global configuration: {key}={value}")

    # Apply source-specific configuration (overrides global)
    for key, value in source_config.items():
        # Convert hyphens to underscores for compatibility with argparse
        arg_key = key.replace("-", "_")

        # Source-specific config overrides global config even if already set from global
        if hasattr(args, arg_key) and key in global_config and getattr(args, arg_key) == global_config[key]:
            setattr(args, arg_key, value)
            logger.debug(f"Overrode global configuration with {args.source} configuration: {key}={value}")
        # Apply source-specific config if not explicitly set on command line
        elif not hasattr(args, arg_key) or getattr(args, arg_key) is None:
            setattr(args, arg_key, value)
            logger.debug(f"Applied {args.source} configuration: {key}={value}")

    # Log the final configuration
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Final configuration:")
        for key in dir(args):
            if not key.startswith("_") and key != "source":
                logger.debug(f"  {key}={getattr(args, key)}")

    return args
