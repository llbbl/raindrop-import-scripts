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


class EvernoteConverter:
    """
    Convert Evernote ENEX files to CSV format for import into Raindrop.io.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the converter.

        Parameters
        ----------
        logger : logging.Logger, optional
            Logger instance to use. If not provided, one will be created.
        """
        self.logger = logger or self._get_or_setup_logger()

    def _get_or_setup_logger(self) -> logging.Logger:
        """
        Get the logger, initializing it if necessary.

        Returns
        -------
        logging.Logger
            The configured logger instance.
        """
        try:
            return get_logger()
        except RuntimeError:
            # Logger not initialized, set it up with default settings
            setup_logging()
            return get_logger()

    @staticmethod
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

    def read_enex_file(self, enex_filename: str) -> str:
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
        self.logger.info(f'Reading input file "{enex_filename}"')
        try:
            with open(enex_filename, "r", encoding="utf-8") as enex_fd:
                return enex_fd.read()
        except Exception:
            self.logger.exception(f"Failed to read ENEX file: {enex_filename}")
            raise

    def parse_enex(self, enex_content: str) -> etree.ElementTree:
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
        self.logger.info("Parsing ENEX content")
        try:
            xml_parser = etree.XMLParser(huge_tree=True, resolve_entities=False)
            xml_tree = etree.fromstring(enex_content.encode('utf-8'), xml_parser)
            return etree.ElementTree(xml_tree)
        except Exception:
            self.logger.exception("Failed to parse ENEX")
            raise

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
            Parsed datetime value.
        """
        try:
            date = isoparse(date_str)
            if date.year == 0:
                # If the year is 0000, use the current year
                now = datetime.datetime.utcnow()
                date = date.replace(year=now.year)
            return date
        except Exception:
            # If parsing fails, return current time
            return datetime.datetime.utcnow()

    def extract_note_records(
        self,
        xml_tree: etree.ElementTree,
        use_markdown: bool,
        filter_tag: Optional[str] = None,
        filter_date_from: Optional[str] = None,
        filter_date_to: Optional[str] = None,
        filter_title: Optional[str] = None,
        filter_url: Optional[str] = None
    ) -> List[Dict]:
        """
        Extract note records from the XML tree.

        Parameters
        ----------
        xml_tree : etree.ElementTree
            Parsed XML tree.
        use_markdown : bool
            Whether to convert note content to Markdown.
        filter_tag : str, optional
            Filter notes by tag.
        filter_date_from : str, optional
            Filter notes by date from.
        filter_date_to : str, optional
            Filter notes by date to.
        filter_title : str, optional
            Filter notes by title.
        filter_url : str, optional
            Filter notes by URL.

        Returns
        -------
        List[Dict]
            List of note records.
        """
        self.logger.info("Extracting note records")
        note_records = []
        root = xml_tree.getroot()

        # Convert filter dates to datetime objects
        date_from = None
        date_to = None
        if filter_date_from:
            date_from = isoparse(filter_date_from)
        if filter_date_to:
            date_to = isoparse(filter_date_to)

        # Process each note
        for note in tqdm(root.xpath("//note"), desc="Processing notes"):
            # Extract basic note data
            title = self.xpath_first_or_default(note, "title", "")
            content = self.xpath_first_or_default(note, "content", "")
            created = self.xpath_first_or_default(note, "created", "", self.parse_xml_date)
            updated = self.xpath_first_or_default(note, "updated", "", self.parse_xml_date)

            # Extract tags
            tags = note.xpath("tag/text()")
            tags_str = "|".join(tags) if tags else ""

            # Extract note attributes
            note_attrs = note.xpath("note-attributes")[0] if note.xpath("note-attributes") else None
            source_url = self.xpath_first_or_default(note_attrs, "source-url", "") if note_attrs else ""
            reminder_time = self.xpath_first_or_default(note_attrs, "reminder-time", "", self.parse_xml_date) if note_attrs else None

            # Apply filters
            if filter_tag and filter_tag not in tags:
                continue
            if filter_date_from and created < date_from:
                continue
            if filter_date_to and created > date_to:
                continue
            if filter_title and filter_title.lower() not in title.lower():
                continue
            if filter_url and filter_url.lower() not in source_url.lower():
                continue

            # Convert content to Markdown if requested
            if use_markdown:
                content = self.html_to_markdown(content)

            # Create note record
            note_record = {
                "title": title,
                "description": content,
                "url": source_url,
                "tags": tags_str,
                "created": created.isoformat() if created else "",
                "updated": updated.isoformat() if updated else "",
                "reminder": reminder_time.isoformat() if reminder_time else ""
            }

            note_records.append(note_record)

        return note_records

    def write_csv(
        self,
        csv_filename: str,
        note_records: List[Dict],
        field_mappings: Optional[Dict[str, str]] = None,
        preview: bool = False,
        preview_limit: int = 10,
        dry_run: bool = False
    ) -> None:
        """
        Write note records to a CSV file.

        Parameters
        ----------
        csv_filename : str
            Output CSV file path.
        note_records : List[Dict]
            List of note records to write.
        field_mappings : Dict[str, str], optional
            Field mappings to apply.
        preview : bool, optional
            Whether to preview the records before writing.
        preview_limit : int, optional
            Number of records to preview.
        dry_run : bool, optional
            Whether to perform a dry run.

        Returns
        -------
        None
        """
        if not note_records:
            self.logger.warning("No notes to write")
            return

        if preview:
            preview_items(note_records, preview_limit)
            if dry_run:
                return

        if dry_run:
            return

        self.logger.info(f'Writing {len(note_records)} notes to "{csv_filename}"')

        # Apply field mappings if provided
        if field_mappings:
            note_records = map_rows(note_records, field_mappings)

        # Write records to CSV
        try:
            with open(csv_filename, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=note_records[0].keys())
                writer.writeheader()
                writer.writerows(note_records)
        except Exception:
            self.logger.exception(f"Failed to write CSV file: {csv_filename}")
            raise

    def convert_enex(self, args: argparse.Namespace) -> None:
        """
        Convert ENEX file to CSV.

        Parameters
        ----------
        args : argparse.Namespace
            Parsed command line arguments.

        Returns
        -------
        None
            The function processes files and doesn't return a value.
        """
        # Validate input and output files
        validate_input_file(args.input_file)
        validate_output_file(args.output_file)

        # Read and parse ENEX file
        enex_content = self.read_enex_file(args.input_file)
        xml_tree = self.parse_enex(enex_content)

        # Get filtering options
        filter_tag = getattr(args, 'filter_tag', None)
        filter_date_from = getattr(args, 'filter_date_from', None)
        filter_date_to = getattr(args, 'filter_date_to', None)
        filter_title = getattr(args, 'filter_title', None)
        filter_url = getattr(args, 'filter_url', None)

        # Log filtering options if any are set
        if any([filter_tag, filter_date_from, filter_date_to, filter_title, filter_url]):
            self.logger.info("Applying filters to notes:")
            if filter_tag:
                self.logger.info(f"  - Tag filter: {filter_tag}")
            if filter_date_from:
                self.logger.info(f"  - Date from: {filter_date_from}")
            if filter_date_to:
                self.logger.info(f"  - Date to: {filter_date_to}")
            if filter_title:
                self.logger.info(f"  - Title contains: {filter_title}")
            if filter_url:
                self.logger.info(f"  - URL contains: {filter_url}")

        # Extract note records with filters
        note_records = self.extract_note_records(
            xml_tree,
            args.use_markdown,
            filter_tag=filter_tag,
            filter_date_from=filter_date_from,
            filter_date_to=filter_date_to,
            filter_title=filter_title,
            filter_url=filter_url
        )

        if len(note_records) <= 0:
            self.logger.error("No records found to convert")
            return

        # Check if dry-run mode is enabled
        dry_run = getattr(args, 'dry_run', False)
        if dry_run:
            self.logger.info("Dry run mode enabled: validating without writing files")

        # Check if preview mode is enabled
        preview = getattr(args, 'preview', False)
        preview_limit = getattr(args, 'preview_limit', 10)
        if preview:
            self.logger.info(f"Preview mode enabled: showing up to {preview_limit} items")

        # Get field mappings
        field_mappings = apply_field_mappings(args)

        # Log field mappings if any are set
        if field_mappings and field_mappings != {
            "title": "title",
            "url": "url",
            "tags": "tags",
            "created": "created",
            "description": "description"
        }:
            self.logger.info("Using custom field mappings:")
            for source, target in field_mappings.items():
                if source != target:
                    self.logger.info(f"  - {source} -> {target}")

        # Write CSV file
        self.write_csv(
            args.output_file,
            note_records,
            field_mappings,
            preview=preview,
            preview_limit=preview_limit,
            dry_run=dry_run
        )

    @staticmethod
    def main():
        try:
            args = EvernoteConverter.parse_command_line_args(sys.argv[1:])
            converter = EvernoteConverter()
            converter.convert_enex(args)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    EvernoteConverter.main()
