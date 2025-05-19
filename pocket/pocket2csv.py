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

from common.cli import create_base_parser, parse_args
from common.logging import setup_logging, get_logger
from common.validation import validate_input_file, validate_output_file

logger = None


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
    parser = create_base_parser("Convert Pocket HTML file to CSV")

    # Update the metavar for input-file to be more specific
    parser._option_string_actions["--input-file"].metavar = "HTMLFILE"
    parser._option_string_actions["--input-file"].help = "Input HTML file path"

    return parse_args(parser, args)


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
    global logger
    parsed_args = parse_command_line_args(sys.argv[1:])
    setup_logging(parsed_args.log_file)
    logger = get_logger()
    convert_html(parsed_args)


if __name__ == "__main__":
    main()
