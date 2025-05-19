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
from datetime import datetime
from bs4 import BeautifulSoup

logger = None


def setup_logging() -> None:
    """
    Initialize console logger and log format.
    """
    global logger
    log_format = "%(asctime)s | %(levelname)8s | %(message)s"
    handlers = [logging.StreamHandler(stream=sys.stdout)]
    logging.basicConfig(handlers=handlers, level=logging.INFO, format=log_format)
    logger = logging.getLogger(__name__)


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
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output-file",
        metavar="CSVFILE",
        help="Output CSV file path",
        type=str,
        required=True,
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

    csv_rows = []
    with open(args.input_file, "r") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    with open(args.output_file, "w") as f:

        for item in soup.find_all("li"):
            url = item.contents[0].get("href")
            title = item.contents[0].string
            tags = item.contents[0].get("tags")

            time_added = float(item.contents[0].get("time_added"))
            date_added = datetime.fromtimestamp(time_added).strftime("%x %X")
            row = {
                "title": title,
                "url": url,
                "created": date_added,
                "tags": tags
            }
            csv_rows.append(row)

        writer = csv.DictWriter(
            f, fieldnames=list(csv_rows[0]), delimiter=",", lineterminator="\n", quotechar='"', quoting=csv.QUOTE_ALL
        )

        writer.writeheader()
        writer.writerows(csv_rows)


def main() -> None:
    setup_logging()
    parsed_args = parse_command_line_args(sys.argv[1:])
    convert_html(parsed_args)


if __name__ == "__main__":
    main()
