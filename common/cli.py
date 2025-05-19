"""
Command line interface functionality for import scripts.

This module provides functions for parsing command line arguments
with consistent patterns across different import scripts.
"""

import argparse
import sys
from typing import List, Optional

from common.validation import validate_input_file, validate_output_file


def create_base_parser(description: str) -> argparse.ArgumentParser:
    """
    Create a base argument parser with common arguments.

    Parameters
    ----------
    description : str
        Description of the script for help text.

    Returns
    -------
    argparse.ArgumentParser
        Base argument parser with common arguments.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--input-file",
        metavar="INPUTFILE",
        help="Input file path",
        type=validate_input_file,
        required=True,
    )
    parser.add_argument(
        "--output-file",
        metavar="CSVFILE",
        help="Output CSV file path",
        type=validate_output_file,
        required=True,
    )
    parser.add_argument(
        "--log-file",
        metavar="LOGFILE",
        help="Log file path (if not specified, logs will only be written to console)",
        type=str,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports without writing files",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview items that will be imported",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        default=10,
        help="Maximum number of items to preview (default: 10)",
    )
    return parser


def parse_args(parser: argparse.ArgumentParser, args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments using the provided parser.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The argument parser to use.
    args : list[str], optional
        Raw command line arguments. If None, sys.argv[1:] will be used.

    Returns
    -------
    argparse.Namespace
        Parsed command line arguments.
    """
    if args is None:
        args = sys.argv[1:]
    return parser.parse_args(args)
