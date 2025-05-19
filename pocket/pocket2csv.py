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


def read_html_file(file_path: str) -> str:
    """
    Read HTML file content.

    Parameters
    ----------
    file_path : str
        HTML file path.

    Returns
    -------
    str
        HTML file content.
    """
    logger.info(f'Reading input file "{file_path}"')
    try:
        with open(file_path, "r") as f:
            return f.read()
    except IOError:
        logger.exception(f"Failed to read input file: {file_path}")
        raise
    except Exception:
        logger.exception("Unexpected error while reading input file")
        raise


def parse_html_content(html_content: str) -> BeautifulSoup:
    """
    Parse HTML content.

    Parameters
    ----------
    html_content : str
        HTML content to parse.

    Returns
    -------
    BeautifulSoup
        Parsed HTML content.
    """
    logger.info("Parsing HTML content")
    try:
        return BeautifulSoup(html_content, "html.parser")
    except Exception:
        logger.exception("Failed to parse HTML")
        raise


def extract_bookmarks(soup: BeautifulSoup) -> list[dict[str, str]]:
    """
    Extract bookmarks from parsed HTML.

    Parameters
    ----------
    soup : BeautifulSoup
        Parsed HTML content.

    Returns
    -------
    list[dict[str, str]]
        Extracted bookmarks.
    """
    logger.info("Extracting bookmarks")
    csv_rows: list[dict[str, str]] = []

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

    return csv_rows


def write_csv_file(file_path: str, csv_rows: list[dict[str, str]], dry_run: bool = False) -> None:
    """
    Write CSV file.

    Parameters
    ----------
    file_path : str
        CSV file path.
    csv_rows : list[dict[str, str]]
        Rows to write to the CSV file.
    dry_run : bool, optional
        If True, validate the rows but don't write to the file.

    Returns
    -------
    None
        The function writes directly to the output file and doesn't return a value.
    """
    if dry_run:
        logger.info(f'Dry run: would write {len(csv_rows)} rows to "{file_path}"')
        # Validate that we can create a CSV writer with the rows
        try:
            fieldnames = list(csv_rows[0])
            # Just create the writer to validate the field names, but don't write anything
            csv.DictWriter(
                None, fieldnames=fieldnames, delimiter=",", lineterminator="\n", quotechar='"', quoting=csv.QUOTE_ALL
            )
            logger.info(f'Dry run: CSV validation successful for "{file_path}"')
        except Exception as e:
            logger.exception(f"Dry run: CSV validation failed: {e}")
            raise
        return

    logger.info(f'Writing CSV output to "{file_path}"')
    try:
        with open(file_path, "w") as f:
            writer = csv.DictWriter(
                f, fieldnames=list(csv_rows[0]), delimiter=",", lineterminator="\n", quotechar='"', quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(csv_rows)
    except IOError:
        logger.exception(f"Failed to write CSV to {file_path}")
        raise
    except Exception:
        logger.exception("Unexpected error while writing CSV")
        raise


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
    # Read and parse HTML file
    html_content = read_html_file(args.input_file)
    soup = parse_html_content(html_content)

    # Extract bookmarks
    csv_rows = extract_bookmarks(soup)

    # Check if we have any bookmarks to write
    if not csv_rows:
        logger.error("No bookmarks found to convert")
        return

    # Check if dry-run mode is enabled
    dry_run = getattr(args, 'dry_run', False)
    if dry_run:
        logger.info("Dry run mode enabled: validating without writing files")

    # Write output file
    write_csv_file(args.output_file, csv_rows, dry_run)

    if dry_run:
        logger.info(f"Dry run: successfully validated {len(csv_rows)} bookmarks")
    else:
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
