"""
Convert Chrome bookmarks JSON export files to CSV format for import into Raindrop.io.

This module provides functionality to parse Chrome bookmarks JSON export files and convert them
to CSV format that can be imported into Raindrop.io bookmark manager. It extracts URLs,
titles, folders (as tags), and creation dates from the Chrome bookmarks JSON export.

To export your bookmarks from Chrome:
1. Open Chrome and go to chrome://bookmarks/
2. Click on the three dots in the top right corner and select "Export bookmarks"
3. Save the file (typically named "bookmarks.html")
4. Use this script to convert it to CSV format for import into Raindrop.io

Usage:
    chrome2csv.py [-h] --input-file JSONFILE --output-file CSVFILE

Example:
    python chrome2csv.py --input-file bookmarks.json --output-file chrome.csv
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tqdm import tqdm

from common.base_converter import BaseConverter
from common.cli import create_base_parser, parse_args
from common.field_mapping import apply_field_mappings, map_rows
from common.logging import get_logger, setup_logging
from common.preview import preview_items

# Define logger at module level but don't initialize it yet
logger = None


@dataclass
class ChromeBookmark:
    """Represents a Chrome bookmark with its metadata."""

    title: str
    url: str
    created: str
    tags: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert the bookmark to a dictionary for CSV writing."""
        return {
            "title": self.title,
            "url": self.url,
            "created": self.created,
            "tags": self.tags,
        }


class ChromeBookmarkConverter(BaseConverter):
    """A class to handle the conversion of Chrome bookmarks from JSON to CSV format."""

    def read_input(self) -> dict[str, Any]:
        """Read and parse the Chrome bookmarks JSON file (BaseConverter hook)."""
        return self.read_json_file()

    def read_json_file(self) -> dict[str, Any]:
        """
        Read and parse the Chrome bookmarks JSON file.

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
            with open(self.input_file, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.exception(f"Failed to parse JSON from file: {self.input_file}")
            raise
        except OSError:
            self.logger.exception(f"Failed to read input file: {self.input_file}")
            raise
        except Exception:
            self.logger.exception("Unexpected error while reading input file")
            raise

    def process_bookmark_node(
        self, node: dict[str, Any], path: list[str] | None = None
    ) -> list[ChromeBookmark]:
        """
        Process a Chrome bookmark node recursively.

        Parameters
        ----------
        node : Dict[str, Any]
            Bookmark node to process.
        path : list[str] | None, optional
            Current path in the bookmark hierarchy, used as tags.

        Returns
        -------
        List[ChromeBookmark]
            List of processed bookmarks.
        """
        if path is None:
            path = []

        results: list[ChromeBookmark] = []

        # Process this node if it's a URL bookmark
        if node.get("type") == "url":
            # Chrome timestamps are in microseconds since Jan 1, 1601 (Windows epoch)
            try:
                chrome_timestamp = int(node.get("date_added", 0))
                if chrome_timestamp > 0:
                    unix_timestamp = chrome_timestamp / 1000000 - 11644473600
                    date_added = datetime.fromtimestamp(unix_timestamp).strftime("%x %X")
                else:
                    date_added = datetime.now().strftime("%x %X")
            except (ValueError, TypeError):
                self.logger.warning(
                    f"Failed to parse timestamp for bookmark "
                    f"{node.get('name', 'Unknown')}, using current time"
                )
                date_added = datetime.now().strftime("%x %X")

            results.append(
                ChromeBookmark(
                    title=node.get("name", "Untitled"),
                    url=node.get("url", ""),
                    created=date_added,
                    tags=",".join(path) if path else "",
                )
            )

        # Process children recursively
        if "children" in node:
            new_path = path.copy()
            if node.get("type") == "folder" and "name" in node:
                new_path.append(node["name"])

            for child in node["children"]:
                results.extend(self.process_bookmark_node(child, new_path))

        return results

    def extract_bookmarks(self, data: dict[str, Any]) -> list[ChromeBookmark]:
        """
        Extract bookmarks from the parsed Chrome JSON data.

        Parameters
        ----------
        data : Dict[str, Any]
            Parsed Chrome bookmarks JSON.

        Returns
        -------
        List[ChromeBookmark]
            Extracted bookmarks sorted by creation date.

        Raises
        ------
        Exception
            If bookmark extraction fails.
        """
        self.logger.info("Extracting bookmarks")
        bookmarks: list[ChromeBookmark] = []

        try:
            roots = data.get("roots", {})
            for root_name, root in roots.items():
                if root_name == "sync_metadata":
                    continue

                # The Chrome bookmark_bar root is conventionally untagged at the top level;
                # other roots use their root name as the first tag.
                initial_path = [root_name] if root_name != "bookmark_bar" else []
                bookmarks.extend(self.process_bookmark_node(root, initial_path))

            self.logger.info(f"Found {len(bookmarks)} bookmarks")
            bookmarks.sort(key=lambda b: b.created)
        except Exception:
            self.logger.exception("Failed to extract bookmarks")
            raise

        return bookmarks

    def write_csv_file(
        self,
        bookmarks: list[ChromeBookmark],
        field_mappings: dict[str, str] | None = None,
        preview: bool = False,
        preview_limit: int = 10,
        dry_run: bool = False,
    ) -> None:
        """
        Write bookmarks to a CSV file with optional field mapping and preview.

        Parameters
        ----------
        bookmarks : List[ChromeBookmark]
            Bookmarks to write to the CSV file.
        field_mappings : Dict[str, str], optional
            Dictionary mapping source fields to target fields.
        preview : bool, optional
            If True, preview the items that will be imported.
        preview_limit : int, optional
            Maximum number of items to preview (default: 10).
        dry_run : bool, optional
            If True, validate the rows but don't write to the file.
        """
        if not bookmarks:
            self.logger.error("No bookmarks to write")
            return

        # Convert bookmarks to dictionaries
        csv_rows = [bookmark.to_dict() for bookmark in bookmarks]

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
                description_field="description"
                if "description" in (mapped_rows[0] if mapped_rows else {})
                else None,
            )

        if dry_run:
            self.logger.info(
                f'Dry run: would write {len(mapped_rows)} rows to "{self.output_file}"'
            )
            try:
                fieldnames = list(mapped_rows[0])
                self.logger.info(f'Dry run: CSV validation successful for "{self.output_file}"')
                if field_mappings:
                    self.logger.info(f"Dry run: Field mappings applied: {field_mappings}")
            except Exception as e:
                self.logger.error(f"Dry run: CSV validation failed: {str(e)}")
                raise
            return

        try:
            with open(self.output_file, "w", encoding="utf-8", newline="") as f:
                fieldnames = list(mapped_rows[0])
                writer = self.new_csv_writer(f, fieldnames)
                writer.writeheader()

                for row in tqdm(mapped_rows, desc="Writing CSV rows"):
                    writer.writerow(row)

            self.logger.info(f'Successfully wrote {len(mapped_rows)} rows to "{self.output_file}"')
        except OSError:
            self.logger.exception(f"Failed to write output file: {self.output_file}")
            raise
        except Exception:
            self.logger.exception("Unexpected error while writing CSV")
            raise

    def convert(
        self,
        field_mappings: dict[str, str] | None = None,
        preview: bool = False,
        preview_limit: int = 10,
        dry_run: bool = False,
    ) -> None:
        """
        Convert Chrome bookmarks from JSON to CSV format.

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
        data = self.read_json_file()
        bookmarks = self.extract_bookmarks(data)
        self.write_csv_file(
            bookmarks,
            field_mappings=field_mappings,
            preview=preview,
            preview_limit=preview_limit,
            dry_run=dry_run,
        )


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
    parser = create_base_parser("Convert Chrome bookmarks JSON file to CSV")
    ChromeBookmarkConverter.configure_input_file_arg(
        parser, "JSONFILE", "Input JSON file path (typically 'Bookmarks' file from Chrome)"
    )
    return parse_args(parser, args)


def convert_json(args: argparse.Namespace) -> None:
    """
    Convert a Chrome bookmarks JSON file to CSV format.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments containing input/output paths and options.
    """
    converter = ChromeBookmarkConverter(args.input_file, args.output_file)
    field_mappings = apply_field_mappings(args)
    converter.convert(
        field_mappings=field_mappings,
        preview=getattr(args, "preview", False),
        preview_limit=getattr(args, "preview_limit", 10),
        dry_run=getattr(args, "dry_run", False),
    )


def main() -> None:
    """Main entry point for the script."""
    global logger
    parsed_args = parse_command_line_args(sys.argv[1:])
    setup_logging(getattr(parsed_args, "log_file", None))
    logger = get_logger()
    convert_json(parsed_args)


if __name__ == "__main__":
    main()
