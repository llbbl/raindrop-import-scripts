import os
import sys
import pytest
import argparse
import tempfile
import datetime
from unittest.mock import patch, MagicMock, mock_open
from lxml import etree
from evernote.enex2csv import (
    parse_command_line_args,
    read_enex_file,
    parse_enex,
    xpath_first_or_default,
    html_to_markdown,
    parse_xml_date,
    extract_note_records,
    write_csv,
    convert_enex,
    main
)


class TestEnex2Csv:
    """Tests for the enex2csv module."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("evernote.enex2csv.logger")
        self.mock_logger = self.logger_patcher.start()

    def teardown_method(self):
        """Tear down the test environment."""
        self.logger_patcher.stop()

    @patch("argparse.ArgumentParser")
    def test_parse_command_line_args(self, mock_arg_parser):
        """Test that parse_command_line_args correctly parses arguments."""
        # Set up mocks
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = argparse.Namespace(input_file="input.enex", output_file="output.csv", use_markdown=True)
        mock_parser.parse_args.return_value = mock_args

        # Test with valid arguments
        args = parse_command_line_args([
            "--input-file", "input.enex",
            "--output-file", "output.csv",
            "--use-markdown"
        ])

        # Check that the returned args are correct
        assert args.input_file == "input.enex"
        assert args.output_file == "output.csv"
        assert args.use_markdown is True

    @patch("builtins.open", new_callable=mock_open, read_data="test content")
    def test_read_enex_file(self, mock_file):
        """Test that read_enex_file correctly reads a file."""
        content = read_enex_file("input.enex")
        mock_file.assert_called_once_with("input.enex", "r", encoding="utf-8")
        assert content == "test content"

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_enex_file_error(self, mock_file):
        """Test that read_enex_file handles errors correctly."""
        with pytest.raises(IOError):
            read_enex_file("nonexistent.enex")

    @patch("lxml.etree.fromstring")
    @patch("lxml.etree.ElementTree")
    def test_parse_enex(self, mock_element_tree, mock_fromstring):
        """Test that parse_enex correctly parses XML content."""
        mock_root = MagicMock()
        mock_fromstring.return_value = mock_root
        mock_tree = MagicMock()
        mock_element_tree.return_value = mock_tree

        result = parse_enex("test content")
        mock_fromstring.assert_called_once()
        mock_element_tree.assert_called_once_with(mock_root)
        assert result == mock_tree

    def test_xpath_first_or_default(self):
        """Test that xpath_first_or_default returns the correct value."""
        # Create a simple XML node
        xml = etree.fromstring("<root><child>value</child></root>")

        # Test with a query that returns a result
        result = xpath_first_or_default(xml, "child", "default")
        assert result == "value"

        # Test with a query that doesn't return a result
        result = xpath_first_or_default(xml, "nonexistent", "default")
        assert result == "default"

        # Test with a formatter
        result = xpath_first_or_default(xml, "child", "default", lambda x: x.upper())
        assert result == "VALUE"

    def test_html_to_markdown(self):
        """Test that html_to_markdown correctly converts HTML to Markdown."""
        html = "<h1>Title</h1><p>Paragraph</p><code>Code</code>"
        markdown = html_to_markdown(html)
        assert "# Title" in markdown
        assert "Paragraph" in markdown
        assert "`Code`" in markdown

    def test_parse_xml_date(self):
        """Test that parse_xml_date correctly parses dates."""
        # Test with a valid date
        date_str = "2020-01-01T12:00:00Z"
        result = parse_xml_date(date_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2020
        assert result.month == 1
        assert result.day == 1

        # Test with a date that has year 0000
        date_str = "0000-01-01T12:00:00Z"
        result = parse_xml_date(date_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == datetime.datetime.utcnow().year

        # Test with an invalid date
        date_str = "invalid date"
        result = parse_xml_date(date_str)
        assert isinstance(result, datetime.datetime)

    @patch("evernote.enex2csv.tqdm")
    def test_extract_note_records(self, mock_tqdm):
        """Test that extract_note_records correctly extracts notes."""
        # Create a mock progress bar
        mock_progress_bar = MagicMock()
        mock_tqdm.return_value = mock_progress_bar

        # Create a simple XML tree with notes
        xml = """
        <en-export>
            <note>
                <title>Note 1</title>
                <content>Content 1</content>
                <created>2020-01-01T12:00:00Z</created>
                <updated>2020-01-02T12:00:00Z</updated>
                <tag>Tag1</tag>
                <tag>Tag2</tag>
                <note-attributes>
                    <source-url>http://example.com</source-url>
                    <reminder-time>2020-01-03T12:00:00Z</reminder-time>
                </note-attributes>
            </note>
            <note>
                <title>Note 2</title>
                <content>Content 2</content>
                <created>2020-02-01T12:00:00Z</created>
                <updated>2020-02-02T12:00:00Z</updated>
                <note-attributes>
                    <source-url>http://example.org</source-url>
                </note-attributes>
            </note>
        </en-export>
        """
        tree = etree.ElementTree(etree.fromstring(xml))

        # Extract notes without Markdown conversion
        records = extract_note_records(tree, False)
        assert len(records) == 2
        assert records[0]["title"] == "Note 1"
        assert records[0]["description"] == "Content 1"
        assert records[0]["url"] == "http://example.com"
        assert records[0]["tags"] == "Tag1|Tag2"
        assert records[1]["title"] == "Note 2"
        assert records[1]["description"] == "Content 2"
        assert records[1]["url"] == "http://example.org"
        assert records[1]["tags"] == ""

        # Extract notes with Markdown conversion
        with patch("evernote.enex2csv.html_to_markdown", return_value="Markdown content"):
            records = extract_note_records(tree, True)
            assert len(records) == 2
            assert records[0]["description"] == "Markdown content"
            assert records[1]["description"] == "Markdown content"

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_write_csv(self, mock_dict_writer, mock_file):
        """Test that write_csv correctly writes records to a CSV file."""
        # Create mock writer
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer

        # Create records
        records = [
            {"title": "Note 1", "description": "Content 1"},
            {"title": "Note 2", "description": "Content 2"}
        ]

        # Write records
        write_csv("output.csv", records)

        # Check that the file was opened
        mock_file.assert_called_once_with("output.csv", "w", encoding="utf-8")

        # Check that the writer was created with the correct fieldnames
        mock_dict_writer.assert_called_once()
        assert mock_dict_writer.call_args[1]["fieldnames"] == ["title", "description"]

        # Check that the header and rows were written
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once_with(records)

    def test_write_csv_dry_run(self):
        """Test that write_csv in dry-run mode doesn't write to a file."""
        # Create records
        records = [
            {"title": "Note 1", "description": "Content 1"},
            {"title": "Note 2", "description": "Content 2"}
        ]

        # Write records in dry-run mode
        with patch("builtins.open") as mock_open:
            write_csv("output.csv", records, dry_run=True)
            mock_open.assert_not_called()

    @patch("evernote.enex2csv.read_enex_file")
    @patch("evernote.enex2csv.parse_enex")
    @patch("evernote.enex2csv.extract_note_records")
    @patch("evernote.enex2csv.write_csv")
    def test_convert_enex(self, mock_write_csv, mock_extract_records, mock_parse_enex, mock_read_file):
        """Test that convert_enex correctly orchestrates the conversion process."""
        # Set up mocks
        mock_read_file.return_value = "enex content"
        mock_tree = MagicMock()
        mock_parse_enex.return_value = mock_tree
        mock_records = [{"title": "Note 1"}, {"title": "Note 2"}]
        mock_extract_records.return_value = mock_records

        # Create args
        args = argparse.Namespace(
            input_file="input.enex",
            output_file="output.csv",
            use_markdown=True,
            dry_run=False
        )

        # Convert
        convert_enex(args)

        # Check that the functions were called with the correct arguments
        mock_read_file.assert_called_once_with("input.enex")
        mock_parse_enex.assert_called_once_with("enex content")
        mock_extract_records.assert_called_once_with(mock_tree, True)
        mock_write_csv.assert_called_once_with("output.csv", mock_records, False)

    @patch("evernote.enex2csv.parse_command_line_args")
    @patch("evernote.enex2csv.setup_logging")
    @patch("evernote.enex2csv.get_logger")
    @patch("evernote.enex2csv.convert_enex")
    def test_main(self, mock_convert_enex, mock_get_logger, mock_setup_logging, mock_parse_args):
        """Test that main correctly sets up the environment and calls convert_enex."""
        # Set up mocks
        mock_args = argparse.Namespace(
            input_file="input.enex",
            output_file="output.csv",
            use_markdown=True,
            log_file="log.txt"
        )
        mock_parse_args.return_value = mock_args
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call main
        main()

        # Check that the functions were called with the correct arguments
        mock_parse_args.assert_called_once_with(sys.argv[1:])
        mock_setup_logging.assert_called_once_with("log.txt")
        mock_get_logger.assert_called_once()
        mock_convert_enex.assert_called_once_with(mock_args)
