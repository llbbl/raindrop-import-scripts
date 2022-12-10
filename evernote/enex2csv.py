"""
Convert Evernote ENEX files to CSV, optionally converting note content to Markdown.

Usage:
enex2csv.py [-h] --input-file ENEXFILE --output-file CSVFILE [--use-markdown]
"""

import argparse
import csv
import datetime
import logging
import sys

from dateutil.parser import isoparse
from html2text import HTML2Text
from lxml import etree

logger = None


def setup_logging():
    """
    Initilialize console logger and log format.
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
    parser = argparse.ArgumentParser(description="Convert Evernote ENEX file to CSV")
    parser.add_argument(
        "--input-file",
        metavar="ENEXFILE",
        help="Input ENEX file path",
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
    parser.add_argument(
        "--use-markdown",
        help="Convert note content to Markdown",
        action="store_true",
    )
    parsed_args = parser.parse_args(args)
    return parsed_args


def read_enex(enex_filename):
    """
    Parse ENEX file as XML.

    Parameters
    ----------
    enex_filename : str
        ENEX file path.

    Returns
    -------
    ElementTree
        Parsed XML tree.
    """
    logger.info(f'Parsing input file "{enex_filename}"')
    with open(enex_filename, "r", encoding="utf-8") as enex_fd:
        try:
            xml_parser = etree.XMLParser(huge_tree=True, resolve_entities=False)
            xml_tree = etree.parse(enex_fd, xml_parser)
            return xml_tree
        except Exception:
            logger.exception("Failed to parse ENEX")
            raise


def xpath_first_or_default(node, query, default, formatter=None):
    """
    Select the first results from an XPath query or fall back to a default value.

    Parameters
    ----------
    node : Element
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


def html_to_markdown(html):
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


def parse_xml_date(date_str):
    """
    Parse an ISO datetime value from ENEX.

    Parameters
    ----------
    date_str : str
        Datetime value stored in the ENEX.

    Returns
    -------
    datetime
        Extracted datetime value.
    """
    if date_str.startswith("0000"):
        date_str = str(datetime.datetime.utcnow().year) + date_str[4:]
    date = isoparse(date_str)
    return date


def extract_note_records(xml_tree, use_markdown):
    """
    Extract notes as dictionaries.

    Parameters
    ----------
    xml_tree : ElementTree
        Parsed ENEX XML tree
    use_markdown : bool
        Whether to convert note content to Markdown. Otherwise, use raw XML/HTML.

    Returns
    -------
    list[dict]
        Extracted note records.
    """
    notes = xml_tree.xpath("//note")
    logger.info(f"Found {len(notes)} notes")
    records = []

    for note in notes:
        title = xpath_first_or_default(note, "title", "")
        logger.info(f'Converting note: "{title}"')

        source_url = xpath_first_or_default(note, "note-attributes/source-url", "")
        content = xpath_first_or_default(note, "content", "")
        created_date = xpath_first_or_default(note, "created", "", parse_xml_date)
        updated_date = xpath_first_or_default(note, "updated", "", parse_xml_date)
        reminder_date = xpath_first_or_default(
            note, "note-attributes/reminder-time", "", parse_xml_date
        )
        tags = "|".join(tag.text for tag in note.xpath("tag"))

        if use_markdown:
            content = html_to_markdown(content)

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

    logger.info(f"{len(records)} notes converted")
    return records


def write_csv(csv_filename, note_records):
    """
    Write parsed note records as CSV.

    Parameters
    ----------
    csv_filename : str
        Output CSV file path.
    records : list[dict]
        Extracted note records.
    """
    logger.info(f'Writing CSV output to "{csv_filename}"')
    with open(csv_filename, "w", encoding="utf-8") as csv_fd:
        writer = csv.DictWriter(
            csv_fd, fieldnames=list(note_records[0]), delimiter=",", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(note_records)


def convert_enex(parsed_args):
    """
    Convert ENEX file to CSV.

    Parameters
    ----------
    parsed_args : argparse.Namespace
        Parsed command line arguments.
    """
    xml_tree = read_enex(parsed_args.input_file)
    records = extract_note_records(xml_tree, parsed_args.use_markdown)
    if len(records) < 0:
        logger.error("No records found to convert")
        return
    write_csv(parsed_args.output_file, records)


def main():
    setup_logging()
    parsed_args = parse_command_line_args(sys.argv[1:])
    convert_enex(parsed_args)


if __name__ == "__main__":
    main()
