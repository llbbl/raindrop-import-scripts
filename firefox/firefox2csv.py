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
from common.field_mapping import apply_field_mappings, map_rows
from common.preview import preview_items


class FirefoxBookmarkConverter:
    """A class to handle the conversion of Firefox bookmarks from JSON to CSV format."""

    def __init__(self, input_file: str, output_file: str, logger=None):
        """
        Initialize the FirefoxBookmarkConverter.

        Parameters
        ----------
        input_file : str
            Path to the input JSON file.
        output_file : str
            Path to the output CSV file.
        logger : Optional[Logger]
            Logger instance for logging messages.
        """
        self.input_file = input_file
        self.output_file = output_file
        self.logger = logger or get_logger(__name__)

    def read_json_file(self) -> Dict[str, Any]:
        """
        Read JSON file content.

        Returns
        -------
        Dict[str, Any]
            Parsed JSON content.

        Raises
        ------
        json.JSONDecodeError
            If the JSON file is malformed.
        IOError
            If the file cannot be read.
        """
        self.logger.info(f'Reading input file "{self.input_file}"')
        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.exception(f"Failed to parse JSON from file: {self.input_file}")
            raise
        except IOError:
            self.logger.exception(f"Failed to read input file: {self.input_file}")
            raise
        except Exception:
            self.logger.exception("Unexpected error while reading input file")
            raise

    def process_bookmark_node(self, node: Dict[str, Any], path: List[str] = None) -> List[Dict[str, str]]:
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
                self.logger.warning(f"Failed to parse timestamp for bookmark {node.get('title', 'Unknown')}, using current time")
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
                results.extend(self.process_bookmark_node(child, new_path))

        return results

    def extract_bookmarks(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
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

        Raises
        ------
        Exception
            If bookmark extraction fails.
        """
        self.logger.info("Extracting bookmarks")
        csv_rows = []

        try:
            # Firefox bookmarks are stored in a nested structure
            # The root has "children" which contains different bookmark folders
            if "children" in data:
                # Process each child of the root
                for child in data["children"]:
                    # Process this child
                    bookmarks = self.process_bookmark_node(child)
                    csv_rows.extend(bookmarks)

            self.logger.info(f"Found {len(csv_rows)} bookmarks")

            # Sort bookmarks by creation date
            csv_rows.sort(key=lambda x: x.get("created", ""))

        except Exception:
            self.logger.exception("Failed to extract bookmarks")
            raise

        return csv_rows

    def write_csv_file(
        self,
        csv_rows: List[Dict[str, str]],
        field_mappings: Optional[Dict[str, str]] = None,
        preview: bool = False,
        preview_limit: int = 10,
        dry_run: bool = False
    ) -> None:
        """
        Write CSV file with optional field mapping and preview.

        Parameters
        ----------
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
        """
        if not csv_rows:
            self.logger.error("No bookmarks to write")
            return

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
            self.logger.info(f'Dry run: would write {len(mapped_rows)} rows to "{self.output_file}"')
            # Validate that we can create a CSV writer with the rows
            try:
                fieldnames = list(mapped_rows[0])
                # Just validate the field names, but don't create a writer
                self.logger.info(f'Dry run: CSV validation successful for "{self.output_file}"')
                if field_mappings:
                    self.logger.info(f'Dry run: Field mappings applied: {field_mappings}')
            except Exception as e:
                self.logger.error(f'Dry run: CSV validation failed: {str(e)}')
                raise
            return

        try:
            with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                if not mapped_rows:
                    self.logger.warning("No rows to write to CSV file")
                    return

                fieldnames = list(mapped_rows[0])
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for row in tqdm(mapped_rows, desc="Writing CSV rows"):
                    writer.writerow(row)

            self.logger.info(f'Successfully wrote {len(mapped_rows)} rows to "{self.output_file}"')

        except Exception:
            self.logger.exception(f"Failed to write CSV file: {self.output_file}")
            raise

    def convert(self, field_mappings: Optional[Dict[str, str]] = None, preview: bool = False,
                preview_limit: int = 10, dry_run: bool = False) -> None:
        """
        Convert Firefox bookmarks from JSON to CSV format.

        Parameters
        ----------
        field_mappings : Dict[str, str], optional
            Dictionary mapping source fields to target fields.
        preview : bool, optional
            If True, preview the items that will be imported.
        preview_limit : int, optional
            Maximum number of items to preview (default: 10).
        dry_run : bool, optional
            If True, validate the rows but don't write to the file.
        """
        # Validate input file
        validate_input_file(self.input_file)

        # Validate output file
        validate_output_file(self.output_file)

        # Read and process the JSON file
        data = self.read_json_file()
        csv_rows = self.extract_bookmarks(data)

        # Write the CSV file
        self.write_csv_file(csv_rows, field_mappings, preview, preview_limit, dry_run)


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


def main() -> None:
    """Main entry point for the script."""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    try:
        # Parse command line arguments
        args = parse_command_line_args(sys.argv[1:])

        # Create converter instance
        converter = FirefoxBookmarkConverter(args.input_file, args.output_file, logger)

        # Convert the bookmarks
        converter.convert(
            field_mappings=args.field_mappings,
            preview=args.preview,
            preview_limit=args.preview_limit,
            dry_run=args.dry_run
        )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
