#!/usr/bin/env python
"""
Test script to verify .env file support.

This script tests that environment variables from a .env file are correctly
loaded and applied to command-line arguments.
"""

import os
import sys
import argparse
from common.config import load_config, apply_config_to_args
from common.logging import setup_logging, get_logger

def main():
    """
    Main entry point for the test script.
    """
    # Set up logging
    setup_logging()
    logger = get_logger()

    # Create a simple argument parser
    parser = argparse.ArgumentParser(description="Test .env file support")
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--dry-run", help="Dry run mode")  # Changed from action="store_true" to accept a value
    parser.add_argument("--api-token", help="API token")
    parser.add_argument("--collection-id", type=int, help="Collection ID")
    parser.add_argument("--batch-size", type=int, help="Batch size")

    # Add a source argument to simulate the main CLI
    parser.add_argument("source", choices=["raindrop-api"], help="Source to import from")

    # Parse arguments
    args = parser.parse_args()

    # Print the initial arguments
    logger.info("Initial arguments:")
    for key in vars(args):
        logger.info(f"  {key}: {getattr(args, key)}")

    # Load configuration
    config = load_config()

    # Print the loaded configuration
    logger.info("Loaded configuration:")
    for section, values in config.items():
        logger.info(f"  {section}:")
        for key, value in values.items():
            logger.info(f"    {key}: {value} ({type(value)})")

    # Apply configuration to arguments
    args = apply_config_to_args(args, config)

    # Print the final arguments
    logger.info("Final arguments after applying configuration:")
    for key in vars(args):
        value = getattr(args, key)
        logger.info(f"  {key}: {value} ({type(value)})")

    # Check if the expected values from .env.test were applied
    expected_values = {
        "log_file": "test.log",
        "dry_run": True,
        "api_token": "test_token_12345",
        "collection_id": 1,
        "batch_size": 10
    }

    all_matched = True
    for key, expected in expected_values.items():
        if hasattr(args, key):
            actual = getattr(args, key)
            # Convert types for comparison if needed
            if isinstance(expected, bool) and isinstance(actual, str):
                actual = actual.lower() == "true"
            elif isinstance(expected, int) and isinstance(actual, str):
                try:
                    actual = int(actual)
                except ValueError:
                    pass

            if actual != expected:
                logger.error(f"Mismatch for {key}: expected {expected} ({type(expected)}), got {actual} ({type(actual)})")
                all_matched = False
        else:
            logger.error(f"Missing argument: {key}")
            all_matched = False

    if all_matched:
        logger.info("All values from .env.test were correctly applied!")
        return 0
    else:
        logger.error("Some values from .env.test were not correctly applied.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
