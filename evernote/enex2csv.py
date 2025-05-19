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

from dateutil.parser import isoparse
from html2text import HTML2Text
from lxml import etree
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
    logger.info(f'Reading input file "{enex_filename}"')
    try:
        with open(enex_filename, "r", encoding="utf-8") as enex_fd:
            return enex_fd.read()
    except Exception:
        logger.exception(f"Failed to read ENEX file: {enex_filename}")
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
    logger.info("Parsing ENEX content")
    try:
        xml_parser = etree.XMLParser(huge_tree=True, resolve_entities=False)
        xml_tree = etree.fromstring(enex_content.encode('utf-8'), xml_parser)
        return etree.ElementTree(xml_tree)
    except Exception:
        logger.exception("Failed to parse ENEX")
        raise


def xpath_first_or_default(node: etree._Element, query: str, default: object, formatter: callable[[str], object] = None) -> object:
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
        logger.exception(f"Failed to parse date: {date_str}")
        # Return current datetime as fallback
        return datetime.datetime.utcnow()
    except Exception:
        logger.exception(f"Unexpected error parsing date: {date_str}")
        # Return current datetime as fallback
        return datetime.datetime.utcnow()


def extract_note_records(xml_tree: etree.ElementTree, use_markdown: bool) -> list[dict]:
    """
    Extract notes as dictionaries.

    Parameters
    ----------
    xml_tree : etree.ElementTree
        Parsed ENEX XML tree
    use_markdown : bool
        Whether to convert note content to Markdown. Otherwise, use raw XML/HTML.

    Returns
    -------
    list[dict]
        Extracted note records.
    """
    try:
        notes = xml_tree.xpath("//note")
        total_notes = len(notes)
        logger.info(f"Found {total_notes} notes")
        records = []

        # Initialize progress bar
        progress_bar = tqdm(total=total_notes, desc="Converting notes", unit="note")

        for i, note in enumerate(notes):
            try:
                title = xpath_first_or_default(note, "title", "")
                logger.debug(f'Converting note: "{title}"')  # Changed to debug to reduce console output

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
                    logger.warning(f"Failed to extract tags for note: {title}")
                    tags = ""

                if use_markdown:
                    try:
                        content = html_to_markdown(content)
                    except Exception:
                        logger.warning(f"Failed to convert HTML to Markdown for note: {title}")
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


def write_csv(csv_filename: str, note_records: list[dict], dry_run: bool = False) -> None:
    """
    Write parsed note records as CSV.

    Parameters
    ----------
    csv_filename : str
        Output CSV file path.
    note_records : list[dict]
        Extracted note records.
    dry_run : bool, optional
        If True, validate the records but don't write to the file.

    Returns
    -------
    None
        The function writes directly to the output file and doesn't return a value.
    """
    if dry_run:
        logger.info(f'Dry run: would write {len(note_records)} records to "{csv_filename}"')
        # Validate that we can create a CSV writer with the records
        try:
            fieldnames = list(note_records[0])
            # Just create the writer to validate the field names, but don't write anything
            csv.DictWriter(
                None, fieldnames=fieldnames, delimiter=",", lineterminator="\n"
            )
            logger.info(f'Dry run: CSV validation successful for "{csv_filename}"')
        except Exception as e:
            logger.exception(f"Dry run: CSV validation failed: {e}")
            raise
        return

    logger.info(f'Writing CSV output to "{csv_filename}"')
    try:
        with open(csv_filename, "w", encoding="utf-8") as csv_fd:
            writer = csv.DictWriter(
                csv_fd, fieldnames=list(note_records[0]), delimiter=",", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(note_records)
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
    records = extract_note_records(xml_tree, parsed_args.use_markdown)
    if len(records) <= 0:
        logger.error("No records found to convert")
        return

    # Check if dry-run mode is enabled
    dry_run = getattr(parsed_args, 'dry_run', False)
    if dry_run:
        logger.info("Dry run mode enabled: validating without writing files")

    write_csv(parsed_args.output_file, records, dry_run)


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
