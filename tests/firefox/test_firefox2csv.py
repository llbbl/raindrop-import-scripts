import os
import sys
import pytest
import argparse
import tempfile
import json
import datetime
from unittest.mock import patch, MagicMock, mock_open
from firefox.firefox2csv import FirefoxBookmarkConverter, parse_command_line_args, main


class TestFirefoxBookmarkConverter:
    """Tests for the FirefoxBookmarkConverter class."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("firefox.firefox2csv.get_logger")
        self.mock_logger = self.logger_patcher.start()
        self.mock_logger.return_value = MagicMock()

        # Create a converter instance for testing
        self.converter = FirefoxBookmarkConverter("input.json", "output.csv", self.mock_logger)

    def teardown_method(self):
        """Tear down the test environment."""
        self.logger_patcher.stop()

    @patch("builtins.open", new_callable=mock_open, read_data='{"children": []}')
    def test_read_json_file(self, mock_file):
        """Test that read_json_file correctly reads a file."""
        content = self.converter.read_json_file()
        mock_file.assert_called_once_with("input.json", "r", encoding="utf-8")
        assert content == {"children": []}

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_json_file_error(self, mock_file):
        """Test that read_json_file handles errors correctly."""
        with pytest.raises(IOError):
            self.converter.read_json_file()

    def test_process_bookmark_node_bookmark(self):
        """Test that process_bookmark_node correctly processes a bookmark node."""
        # Create a bookmark node
        node = {
            "type": "bookmark",
            "title": "Example",
            "uri": "http://example.com",
            "dateAdded": "1577836800000000"  # Firefox timestamp (microseconds since Jan 1, 1970)
        }

        # Process the node
        bookmarks = self.converter.process_bookmark_node(node, ["Folder1", "Folder2"])

        # Check the result
        assert len(bookmarks) == 1
        assert bookmarks[0]["title"] == "Example"
        assert bookmarks[0]["url"] == "http://example.com"
        assert bookmarks[0]["tags"] == "Folder1,Folder2"
        assert "created" in bookmarks[0]

    def test_process_bookmark_node_folder(self):
        """Test that process_bookmark_node correctly processes a folder node with children."""
        # Create a folder node with children
        node = {
            "type": "folder",
            "title": "Folder3",
            "children": [
                {
                    "type": "bookmark",
                    "title": "Example 1",
                    "uri": "http://example1.com",
                    "dateAdded": "1577836800000000"
                },
                {
                    "type": "bookmark",
                    "title": "Example 2",
                    "uri": "http://example2.com",
                    "dateAdded": "1577836800000000"
                }
            ]
        }

        # Process the node
        bookmarks = self.converter.process_bookmark_node(node, ["Folder1", "Folder2"])

        # Check the result
        assert len(bookmarks) == 2
        assert bookmarks[0]["title"] == "Example 1"
        assert bookmarks[0]["url"] == "http://example1.com"
        assert bookmarks[0]["tags"] == "Folder1,Folder2,Folder3"
        assert bookmarks[1]["title"] == "Example 2"
        assert bookmarks[1]["url"] == "http://example2.com"
        assert bookmarks[1]["tags"] == "Folder1,Folder2,Folder3"

    def test_extract_bookmarks(self):
        """Test that extract_bookmarks correctly extracts bookmarks from Firefox JSON."""
        # Create a simple Firefox bookmarks JSON structure
        data = {
            "children": [
                {
                    "type": "folder",
                    "title": "Bookmarks Menu",
                    "children": [
                        {
                            "type": "bookmark",
                            "title": "Example 1",
                            "uri": "http://example1.com",
                            "dateAdded": "1577836800000000"
                        }
                    ]
                },
                {
                    "type": "folder",
                    "title": "Bookmarks Toolbar",
                    "children": [
                        {
                            "type": "bookmark",
                            "title": "Example 2",
                            "uri": "http://example2.com",
                            "dateAdded": "1577836800000000"
                        }
                    ]
                }
            ]
        }

        # Extract bookmarks
        bookmarks = self.converter.extract_bookmarks(data)

        # Check the result
        assert len(bookmarks) == 2
        # Bookmarks are sorted by creation date, so the order might vary
        titles = [b["title"] for b in bookmarks]
        assert "Example 1" in titles
        assert "Example 2" in titles
        urls = [b["url"] for b in bookmarks]
        assert "http://example1.com" in urls
        assert "http://example2.com" in urls

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_write_csv_file(self, mock_dict_writer, mock_file):
        """Test that write_csv_file correctly writes records to a CSV file."""
        # Create mock writer
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer

        # Create records
        records = [
            {"title": "Example 1", "url": "http://example1.com", "created": "01/01/2020 00:00:00", "tags": "Folder1,Folder2"},
            {"title": "Example 2", "url": "http://example2.com", "created": "01/01/2020 00:00:00", "tags": "Folder3"}
        ]

        # Write records
        self.converter.write_csv_file(records)

        # Check that the file was opened
        mock_file.assert_called_once_with("output.csv", "w", newline="", encoding="utf-8")

        # Check that the writer was created with the correct fieldnames
        mock_dict_writer.assert_called_once()
        assert mock_dict_writer.call_args[1]["fieldnames"] == ["title", "url", "created", "tags"]

        # Check that the header and rows were written
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerow.assert_called()

    def test_write_csv_file_dry_run(self):
        """Test that write_csv_file in dry-run mode doesn't write to a file."""
        # Create records
        records = [
            {"title": "Example 1", "url": "http://example1.com", "created": "01/01/2020 00:00:00", "tags": "Folder1,Folder2"},
            {"title": "Example 2", "url": "http://example2.com", "created": "01/01/2020 00:00:00", "tags": "Folder3"}
        ]

        # Write records in dry-run mode
        with patch("builtins.open") as mock_open:
            self.converter.write_csv_file(records, dry_run=True)
            mock_open.assert_not_called()

    @patch("os.access", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("firefox.firefox2csv.FirefoxBookmarkConverter.read_json_file")
    @patch("firefox.firefox2csv.FirefoxBookmarkConverter.extract_bookmarks")
    @patch("firefox.firefox2csv.FirefoxBookmarkConverter.write_csv_file")
    def test_convert(self, mock_write_csv, mock_extract_bookmarks, mock_read_file, mock_exists, mock_isfile, mock_access):
        """Test that convert correctly orchestrates the conversion process."""
        # Set up mocks
        mock_read_file.return_value = {"children": []}
        mock_bookmarks = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_extract_bookmarks.return_value = mock_bookmarks

        # Convert
        self.converter.convert()

        # Check that the methods were called with the correct arguments
        mock_read_file.assert_called_once()
        mock_extract_bookmarks.assert_called_once_with({"children": []})
        mock_write_csv.assert_called_once_with(mock_bookmarks, None, False, 10, False)

    @patch("os.access", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("firefox.firefox2csv.FirefoxBookmarkConverter.read_json_file")
    @patch("firefox.firefox2csv.FirefoxBookmarkConverter.extract_bookmarks")
    @patch("firefox.firefox2csv.FirefoxBookmarkConverter.write_csv_file")
    def test_convert_no_bookmarks(self, mock_write_csv, mock_extract_bookmarks, mock_read_file, mock_exists, mock_isfile, mock_access):
        """Test that convert handles the case where no bookmarks are found."""
        # Set up mocks
        mock_read_file.return_value = {"children": []}
        mock_extract_bookmarks.return_value = []

        # Convert
        self.converter.convert()

        # Check that write_csv_file was called with an empty list
        mock_write_csv.assert_called_once_with([], None, False, 10, False)


class TestCommandLine:
    """Tests for command line functionality."""

    @patch("argparse.ArgumentParser")
    def test_parse_command_line_args(self, mock_arg_parser):
        """Test that parse_command_line_args correctly parses arguments."""
        # Set up mocks
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = argparse.Namespace(input_file="input.json", output_file="output.csv")
        mock_parser.parse_args.return_value = mock_args

        # Test with valid arguments
        args = parse_command_line_args([
            "--input-file", "input.json",
            "--output-file", "output.csv"
        ])

        # Check that the returned args are correct
        assert args.input_file == "input.json"
        assert args.output_file == "output.csv"

    @patch("firefox.firefox2csv.FirefoxBookmarkConverter")
    @patch("firefox.firefox2csv.parse_command_line_args")
    @patch("firefox.firefox2csv.setup_logging")
    @patch("firefox.firefox2csv.get_logger")
    def test_main(self, mock_get_logger, mock_setup_logging, mock_parse_args, mock_converter_class):
        """Test that main correctly sets up and runs the converter."""
        # Set up mocks
        mock_args = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
            field_mappings=None,
            preview=False,
            preview_limit=10,
            dry_run=False
        )
        mock_parse_args.return_value = mock_args
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        # Run main
        main()

        # Check that the converter was created and run correctly
        mock_converter_class.assert_called_once_with("input.json", "output.csv", mock_get_logger.return_value)
        mock_converter.convert.assert_called_once_with(
            field_mappings=None,
            preview=False,
            preview_limit=10,
            dry_run=False
        )
