#!/usr/bin/env python
"""
Unified CLI for importing data into Raindrop.io.

This script provides a unified command-line interface for importing data from various
sources into Raindrop.io. It uses a plugin architecture to support multiple import sources.

Usage:
    raindrop_import.py [-h] {source} ...

Example:
    raindrop_import.py evernote --input-file export.enex --output-file evernote.csv --use-markdown
    raindrop_import.py pocket --input-file ril_export.html --output-file pocket.csv
"""

import argparse
import sys
from typing import List, Optional

from common.config import load_config, apply_config_to_args
from common.logging import setup_logging, get_logger
from common.plugins import PluginRegistry


def create_main_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser for the unified CLI.

    Returns
    -------
    argparse.ArgumentParser
        The main argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Import data from various sources into Raindrop.io",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add global arguments
    parser.add_argument(
        "--log-file",
        metavar="LOGFILE",
        help="Log file path (if not specified, logs will only be written to console)",
        type=str,
    )
    parser.add_argument(
        "--config-file",
        metavar="CONFIG",
        help="Configuration file path (if not specified, default locations will be searched)",
        type=str,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports without writing files",
    )

    return parser


def main(args: Optional[List[str]] = None) -> None:
    """
    Main entry point for the unified CLI.

    Parameters
    ----------
    args : list[str], optional
        Raw command line arguments. If None, sys.argv[1:] will be used.

    Returns
    -------
    None
    """
    if args is None:
        args = sys.argv[1:]

    # Discover all available plugins
    PluginRegistry.discover_plugins()
    available_plugins = PluginRegistry.get_all_plugins()

    if not available_plugins:
        print("Error: No import plugins found.")
        sys.exit(1)

    # Create the main parser
    parser = create_main_parser()

    # Create subparsers for each plugin
    subparsers = parser.add_subparsers(
        title="import sources",
        dest="source",
        help="Source to import from",
        required=True,
    )

    # Add a subparser for each plugin
    for name, plugin_class in available_plugins.items():
        plugin_parser = plugin_class.create_parser()
        subparser = subparsers.add_parser(
            name,
            help=plugin_class.get_description(),
            description=plugin_class.get_description(),
            parents=[plugin_parser],
            conflict_handler="resolve",
        )

        # Remove arguments from the subparser that are handled by the main parser
        for arg in ["--log-file", "--config-file"]:
            if arg in subparser._option_string_actions:
                subparser._option_string_actions.pop(arg)
                for action in subparser._actions[:]:
                    if arg in action.option_strings:
                        subparser._actions.remove(action)

    # Parse the arguments
    parsed_args = parser.parse_args(args)

    # Set up logging
    setup_logging(parsed_args.log_file)
    logger = get_logger()

    # Load configuration
    config = load_config(parsed_args.config_file)

    # Apply configuration to arguments
    parsed_args = apply_config_to_args(parsed_args, config)

    # Log the configuration file used
    if parsed_args.config_file:
        logger.info(f"Using configuration file: {parsed_args.config_file}")
    elif config:
        logger.info("Using configuration from default location")

    # Log the dry run status
    if parsed_args.dry_run:
        logger.info("Running in dry-run mode (no files will be written)")

    # Get the selected plugin
    source = parsed_args.source
    plugin_class = PluginRegistry.get_plugin(source)

    if not plugin_class:
        logger.error(f"Unknown import source: {source}")
        sys.exit(1)

    # Convert the input file
    try:
        plugin_class.convert(parsed_args)
        logger.info(f"Successfully imported data from {source}")
    except Exception as e:
        logger.exception(f"Failed to import data from {source}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
