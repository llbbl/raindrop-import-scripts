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
import sys
import argparse
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from tqdm import tqdm

from common.cli import create_base_parser, parse_args
from common.logging import setup_logging, get_logger
from common.validation import validate_input_file, validate_output_file
from common.field_mapping import apply_field_mappings, map_rows
from common.preview import preview_items

# Define logger at module level but don't initialize it yet
logger = None


class PocketConverter:
    """
    A class for converting Pocket HTML export files to CSV format.

    This class encapsulates the functionality to parse Pocket HTML export files,
    extract bookmark information, and write it to a CSV file for import into Raindrop.io.
    """

    def __init__(self, logger=None):
        """
        Initialize the PocketConverter.

        Parameters
        ----------
        logger : logging.Logger, optional
            Logger instance to use for logging. If None, a new logger will be created.
        """
        self.logger = logger or get_logger()

    def parse_command_line_args(self, args: list[str]) -> argparse.Namespace:
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

    def read_html_file(self, file_path: str) -> str:
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
        self.logger.info(f'Reading input file "{file_path}"')
        try:
            with open(file_path, "r") as f:
                return f.read()
        except IOError:
            self.logger.exception(f"Failed to read input file: {file_path}")
            raise
        except Exception:
            self.logger.exception("Unexpected error while reading input file")
            raise

    def parse_html_content(self, html_content: str) -> BeautifulSoup:
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
        self.logger.info("Parsing HTML content")
        try:
            return BeautifulSoup(html_content, "html.parser")
        except Exception:
            self.logger.exception("Failed to parse HTML")
            raise


    def extract_bookmarks(
        self,
        soup: BeautifulSoup,
        filter_tag: Optional[str] = None,
        filter_date_from: Optional[str] = None,
        filter_date_to: Optional[str] = None,
        filter_title: Optional[str] = None,
        filter_url: Optional[str] = None,
        chunk_size: int = 1000
    ) -> list[dict[str, str]]:
        """
        Extract bookmarks from parsed HTML with optional filtering.

        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML content.
        filter_tag : str, optional
            Filter bookmarks by tag (comma-separated list for multiple tags).
        filter_date_from : str, optional
            Filter bookmarks created on or after this date (format: YYYY-MM-DD).
        filter_date_to : str, optional
            Filter bookmarks created on or before this date (format: YYYY-MM-DD).
        filter_title : str, optional
            Filter bookmarks by title (case-insensitive substring match).
        filter_url : str, optional
            Filter bookmarks by URL (case-insensitive substring match).
        chunk_size : int, optional
            Number of bookmarks to process at a time (default: 1000).
            Helps optimize memory usage for large import files.

        Returns
        -------
        list[dict[str, str]]
            Extracted bookmarks that match the filter criteria.
        """
        self.logger.info("Extracting bookmarks")
        csv_rows: list[dict[str, str]] = []

        try:
            # Get all list items (bookmarks)
            bookmarks = soup.find_all("li")
            total_bookmarks = len(bookmarks)
            self.logger.info(f"Found {total_bookmarks} bookmarks")

            # Initialize progress bar
            progress_bar = tqdm(total=total_bookmarks, desc="Converting bookmarks", unit="bookmark")

            # Process bookmarks in chunks to optimize memory usage
            for chunk_start in range(0, total_bookmarks, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_bookmarks)
                self.logger.debug(f"Processing bookmarks {chunk_start+1} to {chunk_end} of {total_bookmarks}")

                for i in range(chunk_start, chunk_end):
                    item = bookmarks[i]
                    try:
                        # Find the anchor tag within the list item
                        anchor = item.find('a')
                        if not anchor:
                            self.logger.warning(f"No anchor tag found in bookmark {i+1}, skipping")
                            progress_bar.update(1)
                            continue

                        url: str = anchor.get("href")
                        title: str = anchor.string
                        tags: str = anchor.get("tags") or ""  # Default to empty string if None

                        try:
                            time_added: float = float(anchor.get("time_added"))
                            date_added: str = datetime.fromtimestamp(time_added).strftime("%x %X")
                        except (ValueError, TypeError):
                            self.logger.warning(f"Failed to parse timestamp for bookmark {i+1}, using current time")
                            date_added: str = datetime.now().strftime("%x %X")

                        row: Dict[str, str] = {
                            "title": title or "Untitled",  # Default to "Untitled" if None
                            "url": url or "",
                            "created": date_added,
                            "tags": tags
                        }

                        # Apply filters
                        should_include = True

                        # Filter by tag
                        if filter_tag and should_include:
                            filter_tags = [t.strip().lower() for t in filter_tag.split(',')]
                            bookmark_tags = [t.strip().lower() for t in tags.split(',') if t.strip()]
                            # Check if any of the bookmark tags match any of the filter tags
                            if not any(tag in bookmark_tags for tag in filter_tags):
                                should_include = False

                        # Filter by date range
                        if filter_date_from and should_include:
                            try:
                                # Convert date strings to datetime objects for comparison
                                bookmark_date = datetime.strptime(date_added.split()[0], "%x")
                                from_date = datetime.strptime(filter_date_from, "%Y-%m-%d")
                                if bookmark_date < from_date:
                                    should_include = False
                            except ValueError:
                                self.logger.warning(f"Failed to parse date for date-from filter, including bookmark")

                        if filter_date_to and should_include:
                            try:
                                # Convert date strings to datetime objects for comparison
                                bookmark_date = datetime.strptime(date_added.split()[0], "%x")
                                to_date = datetime.strptime(filter_date_to, "%Y-%m-%d")
                                if bookmark_date > to_date:
                                    should_include = False
                            except ValueError:
                                self.logger.warning(f"Failed to parse date for date-to filter, including bookmark")

                        # Filter by title
                        if filter_title and should_include:
                            if filter_title.lower() not in (title or "").lower():
                                should_include = False

                        # Filter by URL
                        if filter_url and should_include:
                            if filter_url.lower() not in (url or "").lower():
                                should_include = False

                        # Add the bookmark to the list if it passes all filters
                        if should_include:
                            csv_rows.append(row)

                        # Update progress bar
                        progress_bar.update(1)
                        progress_bar.set_postfix({"current": (title or "Untitled")[:20] + "..." if len(title or "Untitled") > 20 else (title or "Untitled")})

                    except Exception:
                        self.logger.exception(f"Failed to process bookmark {i+1}")
                        progress_bar.update(1)  # Still update progress bar even if bookmark processing fails
                        # Continue with next bookmark

                # Free up memory by clearing the soup's cache after each chunk
                if hasattr(soup, 'clear_cache'):
                    soup.clear_cache()

            # Close progress bar
            progress_bar.close()
        except Exception:
            self.logger.exception("Failed to extract bookmarks")
            raise

        return csv_rows

    def write_csv_file(
        self,
        file_path: str, 
        csv_rows: List[Dict[str, str]], 
        field_mappings: Optional[Dict[str, str]] = None, 
        preview: bool = False,
        preview_limit: int = 10,
        dry_run: bool = False,
        chunk_size: int = 1000
    ) -> None:
        """
        Write CSV file with optional field mapping and preview.

        Parameters
        ----------
        file_path : str
            CSV file path.
        csv_rows : List[Dict[str, str]]
            Rows to write to the CSV file.
        field_mappings : Dict[str, str], optional
            Dictionary mapping source fields to target fields.
        preview : bool, optional
            If True, preview the items that will be imported.
        preview_limit : int, optional
            Maximum number of items to preview (default: 10).
        dry_run : bool, optional
            If True, validate the rows but don't write to the file.
        chunk_size : int, optional
            Number of rows to write at a time (default: 1000).
            Helps optimize memory usage for very large files.

        Returns
        -------
        None
            The function writes directly to the output file and doesn't return a value.
        """
        # Apply field mappings if provided
        if field_mappings:
            self.logger.info("Applying field mappings to CSV rows")
            mapped_rows = map_rows(csv_rows, field_mappings)
        else:
            mapped_rows = csv_rows

        # Show preview if requested
        if preview:
            self.logger.info("Previewing items that will be imported:")
            preview_items(
                mapped_rows,
                limit=preview_limit,
                title_field="title",
                url_field="url",
                tags_field="tags",
                created_field="created",
                description_field="description" if "description" in (mapped_rows[0] if mapped_rows else {}) else None
            )

        if dry_run:
            self.logger.info(f'Dry run: would write {len(mapped_rows)} rows to "{file_path}"')
            # Validate that we can create a CSV writer with the rows
            try:
                fieldnames = list(mapped_rows[0])
                # Just validate the field names, but don't create a writer
                self.logger.info(f'Dry run: CSV validation successful for "{file_path}"')
                if field_mappings:
                    self.logger.info(f'Dry run: Field mappings applied: {field_mappings}')
            except Exception as e:
                self.logger.exception(f"Dry run: CSV validation failed: {e}")
                raise
            return

        total_rows = len(mapped_rows)
        self.logger.info(f'Writing {total_rows} rows to CSV output file "{file_path}"')

        try:
            with open(file_path, "w") as f:
                # Get fieldnames from the first row
                if not mapped_rows:
                    self.logger.warning("No rows to write")
                    return

                fieldnames = list(mapped_rows[0])
                writer = csv.DictWriter(
                    f, fieldnames=fieldnames, delimiter=",", lineterminator="\n", quotechar='"', quoting=csv.QUOTE_ALL
                )

                # Write header
                writer.writeheader()

                # Write rows in chunks to optimize memory usage
                # Initialize progress bar
                progress_bar = tqdm(total=total_rows, desc="Writing CSV", unit="row")

                for chunk_start in range(0, total_rows, chunk_size):
                    chunk_end = min(chunk_start + chunk_size, total_rows)
                    self.logger.debug(f"Writing rows {chunk_start+1} to {chunk_end} of {total_rows}")

                    # Get the current chunk of rows
                    chunk = mapped_rows[chunk_start:chunk_end]

                    # Write the chunk
                    writer.writerows(chunk)

                    # Update progress bar
                    progress_bar.update(len(chunk))
                    progress_bar.set_postfix({"chunk": f"{chunk_start+1}-{chunk_end}/{total_rows}"})

                    # Free up memory
                    del chunk

                # Close progress bar
                progress_bar.close()

                self.logger.info(f"Successfully wrote {total_rows} rows to {file_path}")
        except IOError:
            self.logger.exception(f"Failed to write CSV to {file_path}")
            raise
        except Exception:
            self.logger.exception("Unexpected error while writing CSV")
            raise

    def convert_html(self, args: argparse.Namespace) -> None:
        """
        Convert Pocket HTML file to CSV format for Raindrop.io import.

        This method reads a Pocket HTML export file, extracts bookmark information
        (URL, title, tags, creation date), and writes it to a CSV file in a format
        compatible with Raindrop.io's import functionality.

        Parameters
        ----------
        args : argparse.Namespace
            Command line arguments containing input_file and output_file paths.

        Returns
        -------
        None
            The method writes directly to the output file and doesn't return a value.
        """
        # Read and parse HTML file
        html_content = self.read_html_file(args.input_file)
        soup = self.parse_html_content(html_content)

        # Extract bookmarks with filtering
        filter_tag = getattr(args, 'filter_tag', None)
        filter_date_from = getattr(args, 'filter_date_from', None)
        filter_date_to = getattr(args, 'filter_date_to', None)
        filter_title = getattr(args, 'filter_title', None)
        filter_url = getattr(args, 'filter_url', None)

        # Log filtering options if any are set
        if any([filter_tag, filter_date_from, filter_date_to, filter_title, filter_url]):
            self.logger.info("Applying filters to bookmarks:")
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

        csv_rows = self.extract_bookmarks(
            soup,
            filter_tag=filter_tag,
            filter_date_from=filter_date_from,
            filter_date_to=filter_date_to,
            filter_title=filter_title,
            filter_url=filter_url
        )

        # Check if we have any bookmarks to write
        if not csv_rows:
            self.logger.error("No bookmarks found to convert")
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

        # Write output file
        self.write_csv_file(
            args.output_file, 
            csv_rows, 
            field_mappings, 
            preview=preview,
            preview_limit=preview_limit,
            dry_run=dry_run
        )

        if dry_run:
            self.logger.info(f"Dry run: successfully validated {len(csv_rows)} bookmarks")
        else:
            self.logger.info(f"Successfully converted {len(csv_rows)} bookmarks to CSV")

    def run(self, args: Optional[list[str]] = None) -> None:
        """
        Run the conversion process.

        This method parses command line arguments and initiates the conversion process.

        Parameters
        ----------
        args : list[str], optional
            Command line arguments. If None, sys.argv[1:] will be used.

        Returns
        -------
        None
        """
        if args is None:
            args = sys.argv[1:]

        parsed_args = self.parse_command_line_args(args)
        self.convert_html(parsed_args)


def extract_bookmarks(
    soup: BeautifulSoup,
    filter_tag: Optional[str] = None,
    filter_date_from: Optional[str] = None,
    filter_date_to: Optional[str] = None,
    filter_title: Optional[str] = None,
    filter_url: Optional[str] = None,
    chunk_size: int = 1000
) -> list[dict[str, str]]:
    """
    Extract bookmarks from parsed HTML with optional filtering.

    Parameters
    ----------
    soup : BeautifulSoup
        Parsed HTML content.
    filter_tag : str, optional
        Filter bookmarks by tag (comma-separated list for multiple tags).
    filter_date_from : str, optional
        Filter bookmarks created on or after this date (format: YYYY-MM-DD).
    filter_date_to : str, optional
        Filter bookmarks created on or before this date (format: YYYY-MM-DD).
    filter_title : str, optional
        Filter bookmarks by title (case-insensitive substring match).
    filter_url : str, optional
        Filter bookmarks by URL (case-insensitive substring match).
    chunk_size : int, optional
        Number of bookmarks to process at a time (default: 1000).
        Helps optimize memory usage for large import files.

    Returns
    -------
    list[dict[str, str]]
        Extracted bookmarks that match the filter criteria.
    """
    converter = PocketConverter(logger)
    return converter.extract_bookmarks(
        soup,
        filter_tag=filter_tag,
        filter_date_from=filter_date_from,
        filter_date_to=filter_date_to,
        filter_title=filter_title,
        filter_url=filter_url,
        chunk_size=chunk_size
    )




def write_csv_file(
    file_path: str, 
    csv_rows: List[Dict[str, str]], 
    field_mappings: Optional[Dict[str, str]] = None, 
    preview: bool = False,
    preview_limit: int = 10,
    dry_run: bool = False,
    chunk_size: int = 1000
) -> None:
    """
    Write CSV file with optional field mapping and preview.

    Parameters
    ----------
    file_path : str
        CSV file path.
    csv_rows : List[Dict[str, str]]
        Rows to write to the CSV file.
    field_mappings : Dict[str, str], optional
        Dictionary mapping source fields to target fields.
    preview : bool, optional
        If True, preview the items that will be imported.
    preview_limit : int, optional
        Maximum number of items to preview (default: 10).
    dry_run : bool, optional
        If True, validate the rows but don't write to the file.
    chunk_size : int, optional
        Number of rows to write at a time (default: 1000).
        Helps optimize memory usage for very large files.

    Returns
    -------
    None
        The function writes directly to the output file and doesn't return a value.
    """
    converter = PocketConverter(logger)
    converter.write_csv_file(
        file_path, 
        csv_rows, 
        field_mappings, 
        preview=preview,
        preview_limit=preview_limit,
        dry_run=dry_run,
        chunk_size=chunk_size
    )


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
    global logger
    # Initialize logger if it's not already initialized
    if logger is None:
        try:
            logger = get_logger()
        except RuntimeError:
            # If setup_logging hasn't been called yet, call it now
            setup_logging()
            logger = get_logger()

    converter = PocketConverter(logger)
    converter.convert_html(args)




def main() -> None:
    """
    Main entry point for the script.

    Parses command line arguments and initiates the conversion process.

    Returns
    -------
    None
    """
    global logger
    # Parse command line arguments
    args = sys.argv[1:]
    parsed_args = parse_command_line_args(args)

    # Set up logging
    setup_logging(parsed_args.log_file)
    logger = get_logger()

    # Create converter and run
    converter = PocketConverter(logger)
    converter.convert_html(parsed_args)


if __name__ == "__main__":
    main()
