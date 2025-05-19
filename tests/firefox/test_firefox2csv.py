import os
import sys
import pytest
import argparse
import tempfile
import json
import datetime
from unittest.mock import patch, MagicMock, mock_open
from firefox.firefox2csv import (
    parse_command_line_args,
    read_json_file,
    process_bookmark_node,
    extract_bookmarks,
    write_csv_file,
    convert_json,
    main
)


class TestFirefox2Csv:
    """Tests for the firefox2csv module."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("firefox.firefox2csv.logger")
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

    @patch("builtins.open", new_callable=mock_open, read_data='{"children": []}')
    def test_read_json_file(self, mock_file):
        """Test that read_json_file correctly reads a file."""
        content = read_json_file("input.json")
        mock_file.assert_called_once_with("input.json", "r", encoding="utf-8")
        assert content == {"children": []}

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_json_file_error(self, mock_file):
        """Test that read_json_file handles errors correctly."""
        with pytest.raises(IOError):
            read_json_file("nonexistent.json")

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
        bookmarks = process_bookmark_node(node, ["Folder1", "Folder2"])

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
        bookmarks = process_bookmark_node(node, ["Folder1", "Folder2"])

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
        bookmarks = extract_bookmarks(data)

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
        write_csv_file("output.csv", records)

        # Check that the file was opened
        mock_file.assert_called_once_with("output.csv", "w", encoding="utf-8", newline="")

        # Check that the writer was created with the correct fieldnames
        mock_dict_writer.assert_called_once()
        assert mock_dict_writer.call_args[1]["fieldnames"] == ["title", "url", "created", "tags"]

        # Check that the header and rows were written
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once_with(records)

    def test_write_csv_file_dry_run(self):
        """Test that write_csv_file in dry-run mode doesn't write to a file."""
        # Create records
        records = [
            {"title": "Example 1", "url": "http://example1.com", "created": "01/01/2020 00:00:00", "tags": "Folder1,Folder2"},
            {"title": "Example 2", "url": "http://example2.com", "created": "01/01/2020 00:00:00", "tags": "Folder3"}
        ]

        # Write records in dry-run mode
        with patch("builtins.open") as mock_open:
            write_csv_file("output.csv", records, dry_run=True)
            mock_open.assert_not_called()

    @patch("firefox.firefox2csv.read_json_file")
    @patch("firefox.firefox2csv.extract_bookmarks")
    @patch("firefox.firefox2csv.write_csv_file")
    def test_convert_json(self, mock_write_csv, mock_extract_bookmarks, mock_read_file):
        """Test that convert_json correctly orchestrates the conversion process."""
        # Set up mocks
        mock_read_file.return_value = {"children": []}
        mock_bookmarks = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_extract_bookmarks.return_value = mock_bookmarks

        # Create args
        args = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
            dry_run=False
        )

        # Convert
        convert_json(args)

        # Check that the functions were called with the correct arguments
        mock_read_file.assert_called_once_with("input.json")
        mock_extract_bookmarks.assert_called_once_with({"children": []})
        mock_write_csv.assert_called_once_with("output.csv", mock_bookmarks, False)

    @patch("firefox.firefox2csv.read_json_file")
    @patch("firefox.firefox2csv.extract_bookmarks")
    @patch("firefox.firefox2csv.write_csv_file")
    def test_convert_json_no_bookmarks(self, mock_write_csv, mock_extract_bookmarks, mock_read_file):
        """Test that convert_json handles the case where no bookmarks are found."""
        # Set up mocks
        mock_read_file.return_value = {"children": []}
        mock_extract_bookmarks.return_value = []

        # Create args
        args = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
            dry_run=False
        )

        # Convert
        convert_json(args)

        # Check that write_csv_file was not called
        mock_write_csv.assert_not_called()

    @patch("firefox.firefox2csv.parse_command_line_args")
    @patch("firefox.firefox2csv.setup_logging")
    @patch("firefox.firefox2csv.get_logger")
    @patch("firefox.firefox2csv.convert_json")
    def test_main(self, mock_convert_json, mock_get_logger, mock_setup_logging, mock_parse_args):
        """Test that main correctly sets up the environment and calls convert_json."""
        # Set up mocks
        mock_args = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
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
        mock_convert_json.assert_called_once_with(mock_args)
