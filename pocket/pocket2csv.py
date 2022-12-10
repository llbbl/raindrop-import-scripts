# parse pocket html export and convert to csv

import csv
import logging
import sys
import argparse
from datetime import datetime
from bs4 import BeautifulSoup

logger = None


def setup_logging():
    """
    Initialize console logger and log format.
    """
    global logger
    log_format = "%(asctime)s | %(levelname)8s | %(message)s"
    handlers = [logging.StreamHandler(stream=sys.stdout)]
    logging.basicConfig(handlers=handlers, level=logging.INFO, format=log_format)
    logger = logging.getLogger(__name__)


def parse_command_line_args(args):
    """
    Parse the arguments passed via the command line.

    Parameters
    ----------
    args : str
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


def convert_html(args):
    """
    Convert Pocket HTML file to CSV.

    :param args:
    :return:
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


def main():
    setup_logging()
    parsed_args = parse_command_line_args(sys.argv[1:])
    convert_html(parsed_args)


if __name__ == "__main__":
    main()
