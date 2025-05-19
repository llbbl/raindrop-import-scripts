"""
File validation functionality for import scripts.

This module provides functions for validating input and output files
to ensure they exist and are accessible.
"""

import os
import argparse
from typing import Optional


def validate_input_file(file_path: str) -> str:
    """
    Validate that the input file exists and is readable.

    Parameters
    ----------
    file_path : str
        Path to the input file.

    Returns
    -------
    str
        The validated file path.

    Raises
    ------
    argparse.ArgumentTypeError
        If the file doesn't exist or isn't readable.
    """
    if not os.path.exists(file_path):
        raise argparse.ArgumentTypeError(f"Input file does not exist: {file_path}")
    if not os.path.isfile(file_path):
        raise argparse.ArgumentTypeError(f"Input path is not a file: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise argparse.ArgumentTypeError(f"Input file is not readable: {file_path}")
    return file_path


def validate_output_file(file_path: str) -> str:
    """
    Validate that the output file path is writable.

    Parameters
    ----------
    file_path : str
        Path to the output file.

    Returns
    -------
    str
        The validated file path.

    Raises
    ------
    argparse.ArgumentTypeError
        If the output directory doesn't exist or isn't writable.
    """
    output_dir = os.path.dirname(file_path) or '.'
    if not os.path.exists(output_dir):
        raise argparse.ArgumentTypeError(f"Output directory does not exist: {output_dir}")
    if not os.access(output_dir, os.W_OK):
        raise argparse.ArgumentTypeError(f"Output directory is not writable: {output_dir}")
    return file_path