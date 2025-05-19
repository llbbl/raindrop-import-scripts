"""
Convert Evernote ENEX files to CSV format for import into Raindrop.io.

This module provides functionality to parse Evernote export files (.enex) and convert them
to CSV format that can be imported into Raindrop.io bookmark manager. It extracts note titles,
content, creation dates, modification dates, tags, and other metadata from the ENEX file.

The module can optionally convert HTML note content to Markdown format for better readability
and compatibility with Raindrop.io's import system.

This is a fork of the project [YuriyGuts/enex2csv](https://github.com/YuriyGuts/enex2csv)
modified specifically to work with raindrop.io's import requirements.

Usage:
    enex2csv.py [-h] --input-file ENEXFILE --output-file CSVFILE [--use-markdown] [--verbose]

Example:
    python enex2csv.py --input-file export.enex --output-file evernote.csv --use-markdown
"""

import argparse
import csv
import datetime
import logging
import os
import sys
import time
from typing import Callable, Optional, List, Dict, Any

from dateutil.parser import isoparse
from html2text import HTML2Text
from lxml import etree
from tqdm import tqdm

from common.cli import create_base_parser, parse_args
from common.logging import setup_logging, get_logger
from common.validation import validate_input_file, validate_output_file
from common.field_mapping import apply_field_mappings, map_rows
from common.preview import preview_items

logger = None


def _get_or_setup_logger() -> logging.Logger:
    """
    Get the logger, initializing it if necessary.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """
    global logger
    if logger is None:
        try:
            logger = get_logger()
        except RuntimeError:
            # Logger not initialized, set it up with default settings
            setup_logging()
            logger = get_logger()
    return logger


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
    parser = create_base_parser("Convert Evernote ENEX file to CSV")
    parser.add_argument(
        "--use-markdown",
        help="Convert note content to Markdown",
        action="store_true",
    )

    # Update the metavar for input-file to be more specific
    parser._option_string_actions["--input-file"].metavar = "ENEXFILE"
    parser._option_string_actions["--input-file"].help = "Input ENEX file path"

    return parse_args(parser, args)


def read_enex_file(enex_filename: str) -> str:
    """
    Read ENEX file content.

    Parameters
    ----------
    enex_filename : str
        ENEX file path.

    Returns
    -------
    str
        ENEX file content.
    """
    _get_or_setup_logger().info(f'Reading input file "{enex_filename}"')
    try:
        with open(enex_filename, "r", encoding="utf-8") as enex_fd:
            return enex_fd.read()
    except Exception:
        _get_or_setup_logger().exception(f"Failed to read ENEX file: {enex_filename}")
        raise


def parse_enex(enex_content: str) -> etree.ElementTree:
    """
    Parse ENEX content as XML.

    Parameters
    ----------
    enex_content : str
        ENEX file content.

    Returns
    -------
    etree.ElementTree
        Parsed XML tree.
    """
    _get_or_setup_logger().info("Parsing ENEX content")
    try:
        xml_parser = etree.XMLParser(huge_tree=True, resolve_entities=False)
        xml_tree = etree.fromstring(enex_content.encode('utf-8'), xml_parser)
        return etree.ElementTree(xml_tree)
    except Exception:
        _get_or_setup_logger().exception("Failed to parse ENEX")
        raise


def xpath_first_or_default(node: etree._Element, query: str, default: object, formatter: Callable[[str], object] = None) -> object:
    """
    Select the first results from an XPath query or fall back to a default value.

    Parameters
    ----------
    node : etree._Element
        XML node.
    query : str
        XPath query.
    default : object
        Default value to fall back to if query returns no results.
    formatter : callable, optional
        Formatter function to convert the results if it is not empty.

    Returns
    -------
    object
        Formatted first query result or default value.
    """
    query_result = node.xpath(query)

    if len(query_result) > 0:
        text = query_result[0].text
        if formatter:
            text = formatter(text)
        return text

    return default


def html_to_markdown(html: str) -> str:
    """
    Convert HTML content to Markdown.

    Parameters
    ----------
    html : str
        HTML content to convert.

    Returns
    -------
    str
        Rendered Markdown.
    """
    converter = HTML2Text()
    converter.mark_code = True
    return converter.handle(html)


def parse_xml_date(date_str: str) -> datetime.datetime:
    """
    Parse an ISO datetime value from ENEX.

    Parameters
    ----------
    date_str : str
        Datetime value stored in the ENEX.

    Returns
    -------
    datetime.datetime
        Extracted datetime value.
    """
    try:
        if date_str.startswith("0000"):
            date_str = str(datetime.datetime.utcnow().year) + date_str[4:]
        date = isoparse(date_str)
        return date
    except ValueError:
        _get_or_setup_logger().exception(f"Failed to parse date: {date_str}")
        # Return current datetime as fallback
        return datetime.datetime.utcnow()
    except Exception:
        _get_or_setup_logger().exception(f"Unexpected error parsing date: {date_str}")
        # Return current datetime as fallback
        return datetime.datetime.utcnow()


def extract_note_records(
    xml_tree: etree.ElementTree, 
    use_markdown: bool,
    filter_tag: Optional[str] = None,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    filter_title: Optional[str] = None,
    filter_url: Optional[str] = None
) -> List[Dict]:
    """
    Extract notes as dictionaries with optional filtering.

    Parameters
    ----------
    xml_tree : etree.ElementTree
        Parsed ENEX XML tree
    use_markdown : bool
        Whether to convert note content to Markdown. Otherwise, use raw XML/HTML.
    filter_tag : str, optional
        Filter notes by tag (comma-separated list for multiple tags).
    filter_date_from : str, optional
        Filter notes created on or after this date (format: YYYY-MM-DD).
    filter_date_to : str, optional
        Filter notes created on or before this date (format: YYYY-MM-DD).
    filter_title : str, optional
        Filter notes by title (case-insensitive substring match).
    filter_url : str, optional
        Filter notes by URL (case-insensitive substring match).

    Returns
    -------
    List[Dict]
        Extracted note records that match the filter criteria.
    """
    try:
        notes = xml_tree.xpath("//note")
        total_notes = len(notes)
        _get_or_setup_logger().info(f"Found {total_notes} notes")
        records = []

        # Initialize progress bar
        progress_bar = tqdm(total=total_notes, desc="Converting notes", unit="note")

        for i, note in enumerate(notes):
            try:
                title = xpath_first_or_default(note, "title", "")
                _get_or_setup_logger().debug(f'Converting note: "{title}"')  # Changed to debug to reduce console output

                source_url = xpath_first_or_default(note, "note-attributes/source-url", "")
                content = xpath_first_or_default(note, "content", "")
                created_date = xpath_first_or_default(note, "created", "", parse_xml_date)
                updated_date = xpath_first_or_default(note, "updated", "", parse_xml_date)
                reminder_date = xpath_first_or_default(
                    note, "note-attributes/reminder-time", "", parse_xml_date
                )

                try:
                    tags = "|".join(tag.text for tag in note.xpath("tag"))
                except Exception:
                    _get_or_setup_logger().warning(f"Failed to extract tags for note: {title}")
                    tags = ""

                if use_markdown:
                    try:
                        content = html_to_markdown(content)
                    except Exception:
                        _get_or_setup_logger().warning(f"Failed to convert HTML to Markdown for note: {title}")
                        # Keep original content if conversion fails

                record = {
                    "title": title,
                    "description": content,
                    "url": source_url,
                    "created": created_date,
                    "updated_date": updated_date,
                    "reminder_date": reminder_date,
                    "tags": tags,
                }

                # Apply filters
                should_include = True

                # Filter by tag
                if filter_tag and should_include:
                    filter_tags = [t.strip().lower() for t in filter_tag.split(',')]
                    note_tags = [t.strip().lower() for t in tags.split('|') if t.strip()]
                    # Check if any of the note tags match any of the filter tags
                    if not any(tag in note_tags for tag in filter_tags):
                        should_include = False

                # Filter by date range
                if filter_date_from and should_include and created_date:
                    try:
                        # Convert date strings to datetime objects for comparison
                        from_date = datetime.datetime.strptime(filter_date_from, "%Y-%m-%d")
                        # created_date is already a datetime object
                        if isinstance(created_date, str):
                            note_date = datetime.datetime.strptime(created_date, "%Y-%m-%d")
                        else:
                            note_date = created_date
                        if note_date < from_date:
                            should_include = False
                    except (ValueError, TypeError):
                        logger.warning(f"Failed to parse date for date-from filter, including note")

                if filter_date_to and should_include and created_date:
                    try:
                        # Convert date strings to datetime objects for comparison
                        to_date = datetime.datetime.strptime(filter_date_to, "%Y-%m-%d")
                        # created_date is already a datetime object
                        if isinstance(created_date, str):
                            note_date = datetime.datetime.strptime(created_date, "%Y-%m-%d")
                        else:
                            note_date = created_date
                        if note_date > to_date:
                            should_include = False
                    except (ValueError, TypeError):
                        logger.warning(f"Failed to parse date for date-to filter, including note")

                # Filter by title
                if filter_title and should_include:
                    if filter_title.lower() not in title.lower():
                        should_include = False

                # Filter by URL
                if filter_url and should_include and source_url:
                    if filter_url.lower() not in source_url.lower():
                        should_include = False

                # Add the note to the list if it passes all filters
                if should_include:
                    records.append(record)

                # Update progress bar
                progress_bar.update(1)
                progress_bar.set_postfix({"current": title[:20] + "..." if len(title) > 20 else title})

            except Exception:
                logger.exception(f"Failed to process note {i+1}")
                progress_bar.update(1)  # Still update progress bar even if note processing fails
                # Continue with next note

        # Close progress bar
        progress_bar.close()
        logger.info(f"{len(records)} notes converted")
        return records
    except Exception:
        logger.exception("Failed to extract note records")
        return []


def write_csv(
    csv_filename: str, 
    note_records: List[Dict], 
    field_mappings: Optional[Dict[str, str]] = None, 
    preview: bool = False,
    preview_limit: int = 10,
    dry_run: bool = False
) -> None:
    """
    Write parsed note records as CSV with optional field mapping and preview.

    Parameters
    ----------
    csv_filename : str
        Output CSV file path.
    note_records : List[Dict]
        Extracted note records.
    field_mappings : Dict[str, str], optional
        Dictionary mapping source fields to target fields.
    preview : bool, optional
        If True, preview the items that will be imported.
    preview_limit : int, optional
        Maximum number of items to preview (default: 10).
    dry_run : bool, optional
        If True, validate the records but don't write to the file.

    Returns
    -------
    None
        The function writes directly to the output file and doesn't return a value.
    """
    # Apply field mappings if provided
    if field_mappings:
        logger.info("Applying field mappings to CSV rows")
        mapped_records = map_rows(note_records, field_mappings)
    else:
        mapped_records = note_records

    # Show preview if requested
    if preview:
        logger.info("Previewing items that will be imported:")
        preview_items(
            mapped_records,
            limit=preview_limit,
            title_field="title",
            url_field="url",
            tags_field="tags",
            created_field="created",
            description_field="description" if "description" in (mapped_records[0] if mapped_records else {}) else None
        )

    if dry_run:
        logger.info(f'Dry run: would write {len(mapped_records)} records to "{csv_filename}"')
        # Validate that we can create a CSV writer with the records
        try:
            fieldnames = list(mapped_records[0])
            # Just validate the field names, but don't create a writer
            logger.info(f'Dry run: CSV validation successful for "{csv_filename}"')
            if field_mappings:
                logger.info(f'Dry run: Field mappings applied: {field_mappings}')
        except Exception as e:
            logger.exception(f"Dry run: CSV validation failed: {e}")
            raise
        return

    logger.info(f'Writing CSV output to "{csv_filename}"')
    try:
        with open(csv_filename, "w", encoding="utf-8") as csv_fd:
            writer = csv.DictWriter(
                csv_fd, fieldnames=list(mapped_records[0]), delimiter=",", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(mapped_records)
    except IOError:
        logger.exception(f"Failed to write CSV to {csv_filename}")
        raise
    except Exception:
        logger.exception("Unexpected error while writing CSV")
        raise


def convert_enex(parsed_args: argparse.Namespace) -> None:
    """
    Convert ENEX file to CSV.

    Parameters
    ----------
    parsed_args : argparse.Namespace
        Parsed command line arguments.

    Returns
    -------
    None
        The function processes files and doesn't return a value.
    """
    enex_content = read_enex_file(parsed_args.input_file)
    xml_tree = parse_enex(enex_content)

    # Get filtering options
    filter_tag = getattr(parsed_args, 'filter_tag', None)
    filter_date_from = getattr(parsed_args, 'filter_date_from', None)
    filter_date_to = getattr(parsed_args, 'filter_date_to', None)
    filter_title = getattr(parsed_args, 'filter_title', None)
    filter_url = getattr(parsed_args, 'filter_url', None)

    # Log filtering options if any are set
    if any([filter_tag, filter_date_from, filter_date_to, filter_title, filter_url]):
        logger.info("Applying filters to notes:")
        if filter_tag:
            logger.info(f"  - Tag filter: {filter_tag}")
        if filter_date_from:
            logger.info(f"  - Date from: {filter_date_from}")
        if filter_date_to:
            logger.info(f"  - Date to: {filter_date_to}")
        if filter_title:
            logger.info(f"  - Title contains: {filter_title}")
        if filter_url:
            logger.info(f"  - URL contains: {filter_url}")

    records = extract_note_records(
        xml_tree, 
        parsed_args.use_markdown,
        filter_tag=filter_tag,
        filter_date_from=filter_date_from,
        filter_date_to=filter_date_to,
        filter_title=filter_title,
        filter_url=filter_url
    )
    if len(records) <= 0:
        logger.error("No records found to convert")
        return

    # Check if dry-run mode is enabled
    dry_run = getattr(parsed_args, 'dry_run', False)
    if dry_run:
        logger.info("Dry run mode enabled: validating without writing files")

    # Check if preview mode is enabled
    preview = getattr(parsed_args, 'preview', False)
    preview_limit = getattr(parsed_args, 'preview_limit', 10)
    if preview:
        logger.info(f"Preview mode enabled: showing up to {preview_limit} items")

    # Get field mappings
    field_mappings = apply_field_mappings(parsed_args)

    # Log field mappings if any are set
    if field_mappings and field_mappings != {
        "title": "title",
        "url": "url",
        "tags": "tags",
        "created": "created",
        "description": "description"
    }:
        logger.info("Using custom field mappings:")
        for source, target in field_mappings.items():
            if source != target:
                logger.info(f"  - {source} -> {target}")

    write_csv(
        parsed_args.output_file, 
        records, 
        field_mappings, 
        preview=preview,
        preview_limit=preview_limit,
        dry_run=dry_run
    )


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
    convert_enex(parsed_args)


if __name__ == "__main__":
    main()
