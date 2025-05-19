"""
Convert Pocket HTML export files to CSV format for import into Raindrop.io.

This module provides functionality to parse Pocket HTML export files and convert them
to CSV format that can be imported into Raindrop.io bookmark manager. It extracts URLs,
titles, tags, and creation dates from the Pocket HTML export.

To export your bookmarks from Pocket, go to https://getpocket.com/export and download
the HTML file. Then use this script to convert it to CSV format for import into Raindrop.io.

Usage:
    pocket2csv.py [-h] --input-file HTMLFILE --output-file CSVFILE

Example:
    python pocket2csv.py --input-file ril_export.html --output-file pocket.csv
"""

import csv
import logging
import sys
import argparse
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm

logger = None


def setup_logging(log_file: str = None) -> None:
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


def parse_command_line_args(args: list[str]) -> argparse.Namespace:
    """
    Parse the arguments passed via the command line.

    Parameters
    ----------
    args : list[str]
        Raw command line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Convert Pocket HTML file to CSV")
    parser.add_argument(
        "--input-file",
        metavar="HTMLFILE",
        help="Input HTML file path",
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
    return parser.parse_args(args)


def convert_html(args: argparse.Namespace) -> None:
    """
    Convert Pocket HTML file to CSV format for Raindrop.io import.

    This function reads a Pocket HTML export file, extracts bookmark information
    (URL, title, tags, creation date), and writes it to a CSV file in a format
    compatible with Raindrop.io's import functionality.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments containing input_file and output_file paths.

    Returns
    -------
    None
        The function writes directly to the output file and doesn't return a value.
    """

    csv_rows: list[dict[str, str]] = []

    # Read input file
    try:
        with open(args.input_file, "r") as f:
            html: str = f.read()
    except IOError:
        logger.exception(f"Failed to read input file: {args.input_file}")
        raise
    except Exception:
        logger.exception("Unexpected error while reading input file")
        raise

    # Parse HTML
    try:
        soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
    except Exception:
        logger.exception("Failed to parse HTML")
        raise

    # Extract bookmark data
    try:
        # Get all list items (bookmarks)
        bookmarks = soup.find_all("li")
        total_bookmarks = len(bookmarks)
        logger.info(f"Found {total_bookmarks} bookmarks")

        # Initialize progress bar
        progress_bar = tqdm(total=total_bookmarks, desc="Converting bookmarks", unit="bookmark")

        for i, item in enumerate(bookmarks):
            try:
                url: str = item.contents[0].get("href")
                title: str = item.contents[0].string
                tags: str = item.contents[0].get("tags") or ""  # Default to empty string if None

                try:
                    time_added: float = float(item.contents[0].get("time_added"))
                    date_added: str = datetime.fromtimestamp(time_added).strftime("%x %X")
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse timestamp for bookmark {i+1}, using current time")
                    date_added: str = datetime.now().strftime("%x %X")

                row: dict[str, str] = {
                    "title": title or "Untitled",  # Default to "Untitled" if None
                    "url": url or "",
                    "created": date_added,
                    "tags": tags
                }
                csv_rows.append(row)

                # Update progress bar
                progress_bar.update(1)
                progress_bar.set_postfix({"current": (title or "Untitled")[:20] + "..." if len(title or "Untitled") > 20 else (title or "Untitled")})

            except Exception:
                logger.exception(f"Failed to process bookmark {i+1}")
                progress_bar.update(1)  # Still update progress bar even if bookmark processing fails
                # Continue with next bookmark

        # Close progress bar
        progress_bar.close()
    except Exception:
        logger.exception("Failed to extract bookmarks")
        raise

    # Check if we have any bookmarks to write
    if not csv_rows:
        logger.error("No bookmarks found to convert")
        return

    # Write output file
    try:
        with open(args.output_file, "w") as f:
            writer = csv.DictWriter(
                f, fieldnames=list(csv_rows[0]), delimiter=",", lineterminator="\n", quotechar='"', quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(csv_rows)
    except IOError:
        logger.exception(f"Failed to write CSV to {args.output_file}")
        raise
    except Exception:
        logger.exception("Unexpected error while writing CSV")
        raise

    logger.info(f"Successfully converted {len(csv_rows)} bookmarks to CSV")


def main() -> None:
    """
    Main entry point for the script.

    Parses command line arguments and initiates the conversion process.

    Returns
    -------
    None
    """
    parsed_args = parse_command_line_args(sys.argv[1:])
    setup_logging(parsed_args.log_file)
    convert_html(parsed_args)


if __name__ == "__main__":
    main()
