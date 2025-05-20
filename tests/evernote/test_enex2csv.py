import os
import sys
import pytest
import argparse
import tempfile
import datetime
from unittest.mock import patch, MagicMock, mock_open
from lxml import etree
from evernote.enex2csv import EvernoteConverter


class TestEvernoteConverter:
    """Tests for the EvernoteConverter class."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("evernote.enex2csv.get_logger")
        self.mock_logger = self.logger_patcher.start()
        self.converter = EvernoteConverter(self.mock_logger)

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
        args = EvernoteConverter.parse_command_line_args([
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
        content = self.converter.read_enex_file("input.enex")
        mock_file.assert_called_once_with("input.enex", "r", encoding="utf-8")
        assert content == "test content"

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_enex_file_error(self, mock_file):
        """Test that read_enex_file handles errors correctly."""
        with pytest.raises(IOError):
            self.converter.read_enex_file("nonexistent.enex")

    @patch("lxml.etree.fromstring")
    @patch("lxml.etree.ElementTree")
    def test_parse_enex(self, mock_element_tree, mock_fromstring):
        """Test that parse_enex correctly parses XML content."""
        mock_root = MagicMock()
        mock_fromstring.return_value = mock_root
        mock_tree = MagicMock()
        mock_element_tree.return_value = mock_tree

        result = self.converter.parse_enex("test content")
        mock_fromstring.assert_called_once()
        mock_element_tree.assert_called_once_with(mock_root)
        assert result == mock_tree

    def test_xpath_first_or_default(self):
        """Test that xpath_first_or_default returns the correct value."""
        # Create a simple XML node
        xml = etree.fromstring("<root><child>value</child></root>")

        # Test with a query that returns a result
        result = self.converter.xpath_first_or_default(xml, "child", "default")
        assert result == "value"

        # Test with a query that doesn't return a result
        result = self.converter.xpath_first_or_default(xml, "nonexistent", "default")
        assert result == "default"

        # Test with a formatter
        result = self.converter.xpath_first_or_default(xml, "child", "default", lambda x: x.upper())
        assert result == "VALUE"

    def test_html_to_markdown(self):
        """Test that html_to_markdown correctly converts HTML to Markdown."""
        html = "<h1>Title</h1><p>Paragraph</p><code>Code</code>"
        markdown = self.converter.html_to_markdown(html)
        assert "# Title" in markdown
        assert "Paragraph" in markdown
        assert "`Code`" in markdown

    def test_parse_xml_date(self):
        """Test that parse_xml_date correctly parses dates."""
        # Test with a valid date
        date_str = "2020-01-01T12:00:00Z"
        result = self.converter.parse_xml_date(date_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2020
        assert result.month == 1
        assert result.day == 1

        # Test with a date that has year 0000
        date_str = "0000-01-01T12:00:00Z"
        result = self.converter.parse_xml_date(date_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == datetime.datetime.utcnow().year

        # Test with an invalid date
        date_str = "invalid date"
        result = self.converter.parse_xml_date(date_str)
        assert isinstance(result, datetime.datetime)

    @patch("evernote.enex2csv.tqdm")
    def test_extract_note_records(self, mock_tqdm):
        """Test that extract_note_records correctly extracts notes."""
        # Make tqdm a passthrough for the iterable
        mock_tqdm.side_effect = lambda x, **kwargs: x

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
        records = self.converter.extract_note_records(tree, False)
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
        with patch("evernote.enex2csv.EvernoteConverter.html_to_markdown", return_value="Markdown content"):
            records = self.converter.extract_note_records(tree, True)
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
        self.converter.write_csv("output.csv", records)

        # Check that the file was opened correctly
        mock_file.assert_called_once_with("output.csv", "w", newline="", encoding="utf-8")

        # Check that the writer was created with the correct fieldnames
        mock_dict_writer.assert_called_once()
        assert list(mock_dict_writer.call_args[1]["fieldnames"]) == ["title", "description"]

        # Check that the header and records were written
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once_with(records)

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_write_csv_dry_run(self, mock_dict_writer, mock_file):
        """Test that write_csv handles dry run correctly."""
        # Create records
        records = [
            {"title": "Note 1", "description": "Content 1"},
            {"title": "Note 2", "description": "Content 2"}
        ]

        # Write records with dry run
        self.converter.write_csv("output.csv", records, dry_run=True)

        # Check that the file was not opened
        mock_file.assert_not_called()

        # Check that the writer was not created
        mock_dict_writer.assert_not_called()

    @patch("common.logging.setup_logging")
    @patch("common.logging.get_logger")
    @patch("evernote.enex2csv.apply_field_mappings", return_value={"title": "name", "description": "content"})
    @patch("os.access", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("evernote.enex2csv.EvernoteConverter.read_enex_file")
    @patch("evernote.enex2csv.EvernoteConverter.parse_enex")
    @patch("evernote.enex2csv.EvernoteConverter.extract_note_records")
    @patch("evernote.enex2csv.EvernoteConverter.write_csv")
    def test_convert_enex(self, mock_write_csv, mock_extract_records, mock_parse_enex, mock_read_file, mock_exists, mock_isfile, mock_access, mock_apply_field_mappings, mock_get_logger, mock_setup_logging):
        """Test that convert_enex correctly converts an ENEX file."""
        # Set up mocks
        mock_read_file.return_value = "test content"
        mock_parse_enex.return_value = "parsed content"
        mock_extract_records.return_value = [{"title": "Note 1"}]
        mock_get_logger.return_value = self.mock_logger

        # Create test args with filters
        args = argparse.Namespace(
            input_file="input.enex",
            output_file="output.csv",
            use_markdown=True,
            filter_tag="test-tag",
            filter_date_from="2020-01-01",
            filter_date_to="2020-12-31",
            filter_title="test",
            filter_url="example.com",
            field_mappings={"title": "name", "description": "content"},
            preview=True,
            preview_limit=5,
            dry_run=True
        )

        # Convert file
        self.converter.convert_enex(args)

        # Check that the file was read
        mock_read_file.assert_called_once_with("input.enex")

        # Check that the content was parsed
        mock_parse_enex.assert_called_once_with("test content")

        # Check that records were extracted with filters
        mock_extract_records.assert_called_once_with(
            "parsed content",
            True,
            filter_tag="test-tag",
            filter_date_from="2020-01-01",
            filter_date_to="2020-12-31",
            filter_title="test",
            filter_url="example.com"
        )

        # Check that records were written with correct parameters
        mock_write_csv.assert_called_once_with(
            "output.csv",
            [{"title": "Note 1"}],
            mock_apply_field_mappings.return_value,
            preview=True,
            preview_limit=5,
            dry_run=True
        )

        # Verify logging calls
        self.mock_logger.info.assert_any_call("Applying filters to notes:")
        self.mock_logger.info.assert_any_call("  - Tag filter: test-tag")
        self.mock_logger.info.assert_any_call("  - Date from: 2020-01-01")
        self.mock_logger.info.assert_any_call("  - Date to: 2020-12-31")
        self.mock_logger.info.assert_any_call("  - Title contains: test")
        self.mock_logger.info.assert_any_call("  - URL contains: example.com")
        self.mock_logger.info.assert_any_call("Dry run mode enabled: validating without writing files")
        self.mock_logger.info.assert_any_call("Preview mode enabled: showing up to 5 items")
        self.mock_logger.info.assert_any_call("Using custom field mappings:")
        self.mock_logger.info.assert_any_call("  - title -> name")
        self.mock_logger.info.assert_any_call("  - description -> content")

    @patch("evernote.enex2csv.EvernoteConverter.parse_command_line_args")
    @patch("evernote.enex2csv.EvernoteConverter")
    def test_main(self, mock_converter_class, mock_parse_args):
        """Test that main correctly handles command line arguments."""
        # Set up mocks
        mock_args = argparse.Namespace(input_file="input.enex", output_file="output.csv")
        mock_parse_args.return_value = mock_args
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        # Call main
        with patch("sys.argv", ["script.py", "--input-file", "input.enex", "--output-file", "output.csv"]):
            EvernoteConverter.main()

        # Check that arguments were parsed
        mock_parse_args.assert_called_once()

        # Check that converter was created
        mock_converter_class.assert_called_once()

        # Check that convert_enex was called
        mock_converter.convert_enex.assert_called_once_with(mock_args)
