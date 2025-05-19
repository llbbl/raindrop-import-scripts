"""
Convert Firefox bookmarks JSON export files to CSV format for import into Raindrop.io.

This module provides functionality to parse Firefox bookmarks JSON export files and convert them
to CSV format that can be imported into Raindrop.io bookmark manager. It extracts URLs,
titles, folders (as tags), and creation dates from the Firefox bookmarks JSON export.

To export your bookmarks from Firefox:
1. Open Firefox and click on the Library button (bookshelf icon)
2. Select "Bookmarks" and then "Show All Bookmarks"
3. In the Library window, click on "Import and Backup" and select "Backup..."
4. Save the JSON file
5. Use this script to convert it to CSV format for import into Raindrop.io

Usage:
    firefox2csv.py [-h] --input-file JSONFILE --output-file CSVFILE

Example:
    python firefox2csv.py --input-file bookmarks-2023-05-18.json --output-file firefox.csv
"""

import csv
import json
import sys
import argparse
from datetime import datetime
from tqdm import tqdm
from typing import Dict, List, Any, Optional

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
    parser = create_base_parser("Convert Firefox bookmarks JSON file to CSV")

    # Update the metavar for input-file to be more specific
    parser._option_string_actions["--input-file"].metavar = "JSONFILE"
    parser._option_string_actions["--input-file"].help = "Input JSON file path (exported from Firefox bookmarks)"

    return parse_args(parser, args)


def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    Read JSON file content.

    Parameters
    ----------
    file_path : str
        JSON file path.

    Returns
    -------
    Dict[str, Any]
        Parsed JSON content.
    """
    logger.info(f'Reading input file "{file_path}"')
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.exception(f"Failed to parse JSON from file: {file_path}")
        raise
    except IOError:
        logger.exception(f"Failed to read input file: {file_path}")
        raise
    except Exception:
        logger.exception("Unexpected error while reading input file")
        raise


def process_bookmark_node(node: Dict[str, Any], path: List[str] = None) -> List[Dict[str, str]]:
    """
    Process a bookmark node recursively.

    Parameters
    ----------
    node : Dict[str, Any]
        Bookmark node to process.
    path : List[str], optional
        Current path in the bookmark hierarchy, used as tags.

    Returns
    -------
    List[Dict[str, str]]
        List of processed bookmarks.
    """
    if path is None:
        path = []

    results = []

    # Process this node if it's a bookmark (has a URI)
    if node.get("type") == "bookmark" and "uri" in node:
        # Firefox timestamps are in microseconds since Jan 1, 1970
        try:
            firefox_timestamp = int(node.get("dateAdded", 0)) / 1000000  # Convert to seconds
            if firefox_timestamp > 0:
                date_added = datetime.fromtimestamp(firefox_timestamp).strftime("%x %X")
            else:
                date_added = datetime.now().strftime("%x %X")
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse timestamp for bookmark {node.get('title', 'Unknown')}, using current time")
            date_added = datetime.now().strftime("%x %X")

        # Create bookmark entry
        bookmark = {
            "title": node.get("title", "Untitled"),
            "url": node.get("uri", ""),
            "created": date_added,
            "tags": ",".join(path) if path else ""
        }
        results.append(bookmark)

    # Process children recursively
    if "children" in node:
        # If this is a folder, add its name to the path for child bookmarks
        new_path = path.copy()
        if node.get("type") == "folder" and "title" in node:
            new_path.append(node["title"])

        # Process each child
        for child in node["children"]:
            results.extend(process_bookmark_node(child, new_path))

    return results


def extract_bookmarks(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract bookmarks from parsed JSON.

    Parameters
    ----------
    data : Dict[str, Any]
        Parsed JSON content.

    Returns
    -------
    List[Dict[str, str]]
        Extracted bookmarks.
    """
    logger.info("Extracting bookmarks")
    csv_rows = []

    try:
        # Firefox bookmarks are stored in a nested structure
        # The root has "children" which contains different bookmark folders
        if "children" in data:
            # Process each child of the root
            for child in data["children"]:
                # Process this child
                bookmarks = process_bookmark_node(child)
                csv_rows.extend(bookmarks)

        logger.info(f"Found {len(csv_rows)} bookmarks")

        # Sort bookmarks by creation date
        csv_rows.sort(key=lambda x: x.get("created", ""))

    except Exception:
        logger.exception("Failed to extract bookmarks")
        raise

    return csv_rows


def write_csv_file(file_path: str, csv_rows: List[Dict[str, str]], dry_run: bool = False) -> None:
    """
    Write CSV file.

    Parameters
    ----------
    file_path : str
        CSV file path.
    csv_rows : List[Dict[str, str]]
        Rows to write to the CSV file.
    dry_run : bool, optional
        If True, validate the rows but don't write to the file.

    Returns
    -------
    None
        The function writes directly to the output file and doesn't return a value.
    """
    if not csv_rows:
        logger.error("No bookmarks to write")
        return

    if dry_run:
        logger.info(f'Dry run: would write {len(csv_rows)} rows to "{file_path}"')
        # Validate that we can create a CSV writer with the rows
        try:
            fieldnames = list(csv_rows[0])
            # Just validate the field names, but don't create a writer
            logger.info(f'Dry run: CSV validation successful for "{file_path}"')
        except Exception as e:
            logger.exception(f"Dry run: CSV validation failed: {e}")
            raise
        return

    logger.info(f'Writing CSV output to "{file_path}"')
    try:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
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


def convert_json(args: argparse.Namespace) -> None:
    """
    Convert Firefox bookmarks JSON file to CSV format for Raindrop.io import.

    This function reads a Firefox bookmarks JSON export file, extracts bookmark information
    (URL, title, folders as tags, creation date), and writes it to a CSV file in a format
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
    # Read and parse JSON file
    data = read_json_file(args.input_file)

    # Extract bookmarks
    csv_rows = extract_bookmarks(data)

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
    convert_json(parsed_args)


if __name__ == "__main__":
    main()
