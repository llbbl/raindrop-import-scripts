import os
import sys
import pytest
import argparse
import tempfile
import datetime
from unittest.mock import patch, MagicMock, mock_open
from bs4 import BeautifulSoup
from pocket.pocket2csv import (
    parse_command_line_args,
    read_html_file,
    parse_html_content,
    extract_bookmarks,
    write_csv_file,
    convert_html,
    main
)


class TestPocket2Csv:
    """Tests for the pocket2csv module."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("pocket.pocket2csv.logger")
        self.mock_logger = self.logger_patcher.start()

    def teardown_method(self):
        """Tear down the test environment."""
        self.logger_patcher.stop()

    def test_parse_command_line_args(self):
        """Test that parse_command_line_args correctly parses arguments."""
        # Test with valid arguments
        args = parse_command_line_args([
            "--input-file", "input.html",
            "--output-file", "output.csv"
        ])
        assert args.input_file == "input.html"
        assert args.output_file == "output.csv"

    @patch("builtins.open", new_callable=mock_open, read_data="test content")
    def test_read_html_file(self, mock_file):
        """Test that read_html_file correctly reads a file."""
        content = read_html_file("input.html")
        mock_file.assert_called_once_with("input.html", "r")
        assert content == "test content"

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_html_file_error(self, mock_file):
        """Test that read_html_file handles errors correctly."""
        with pytest.raises(IOError):
            read_html_file("nonexistent.html")

    @patch("bs4.BeautifulSoup")
    def test_parse_html_content(self, mock_bs):
        """Test that parse_html_content correctly parses HTML content."""
        mock_soup = MagicMock()
        mock_bs.return_value = mock_soup

        result = parse_html_content("test content")
        mock_bs.assert_called_once_with("test content", "html.parser")
        assert result == mock_soup

    @patch("pocket.pocket2csv.tqdm")
    def test_extract_bookmarks(self, mock_tqdm):
        """Test that extract_bookmarks correctly extracts bookmarks."""
        # Create a mock progress bar
        mock_progress_bar = MagicMock()
        mock_tqdm.return_value = mock_progress_bar
        
        # Create a simple HTML soup with bookmarks
        html = """
        <html>
            <body>
                <ul>
                    <li>
                        <a href="http://example.com" time_added="1577836800" tags="tag1,tag2">Example 1</a>
                    </li>
                    <li>
                        <a href="http://example.org" time_added="1580515200">Example 2</a>
                    </li>
                </ul>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract bookmarks
        bookmarks = extract_bookmarks(soup)
        assert len(bookmarks) == 2
        assert bookmarks[0]["title"] == "Example 1"
        assert bookmarks[0]["url"] == "http://example.com"
        assert bookmarks[0]["tags"] == "tag1,tag2"
        assert bookmarks[1]["title"] == "Example 2"
        assert bookmarks[1]["url"] == "http://example.org"
        assert bookmarks[1]["tags"] == ""
        
        # Check that the progress bar was updated
        assert mock_progress_bar.update.call_count == 2
        assert mock_progress_bar.close.call_count == 1

    @patch("pocket.pocket2csv.tqdm")
    def test_extract_bookmarks_with_errors(self, mock_tqdm):
        """Test that extract_bookmarks handles errors correctly."""
        # Create a mock progress bar
        mock_progress_bar = MagicMock()
        mock_tqdm.return_value = mock_progress_bar
        
        # Create a simple HTML soup with a malformed bookmark
        html = """
        <html>
            <body>
                <ul>
                    <li>
                        <a href="http://example.com" time_added="invalid">Example 1</a>
                    </li>
                </ul>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract bookmarks
        bookmarks = extract_bookmarks(soup)
        assert len(bookmarks) == 1
        assert bookmarks[0]["title"] == "Example 1"
        assert bookmarks[0]["url"] == "http://example.com"
        
        # Check that the progress bar was updated
        assert mock_progress_bar.update.call_count == 1
        assert mock_progress_bar.close.call_count == 1

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_write_csv_file(self, mock_dict_writer, mock_file):
        """Test that write_csv_file correctly writes records to a CSV file."""
        # Create mock writer
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer
        
        # Create records
        records = [
            {"title": "Example 1", "url": "http://example.com", "tags": "tag1,tag2"},
            {"title": "Example 2", "url": "http://example.org", "tags": ""}
        ]
        
        # Write records
        write_csv_file("output.csv", records)
        
        # Check that the file was opened
        mock_file.assert_called_once_with("output.csv", "w")
        
        # Check that the writer was created with the correct fieldnames
        mock_dict_writer.assert_called_once()
        assert mock_dict_writer.call_args[1]["fieldnames"] == ["title", "url", "tags"]
        
        # Check that the header and rows were written
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once_with(records)

    def test_write_csv_file_dry_run(self):
        """Test that write_csv_file in dry-run mode doesn't write to a file."""
        # Create records
        records = [
            {"title": "Example 1", "url": "http://example.com", "tags": "tag1,tag2"},
            {"title": "Example 2", "url": "http://example.org", "tags": ""}
        ]
        
        # Write records in dry-run mode
        with patch("builtins.open") as mock_open:
            write_csv_file("output.csv", records, dry_run=True)
            mock_open.assert_not_called()

    @patch("pocket.pocket2csv.read_html_file")
    @patch("pocket.pocket2csv.parse_html_content")
    @patch("pocket.pocket2csv.extract_bookmarks")
    @patch("pocket.pocket2csv.write_csv_file")
    def test_convert_html(self, mock_write_csv, mock_extract_bookmarks, mock_parse_html, mock_read_file):
        """Test that convert_html correctly orchestrates the conversion process."""
        # Set up mocks
        mock_read_file.return_value = "html content"
        mock_soup = MagicMock()
        mock_parse_html.return_value = mock_soup
        mock_bookmarks = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_extract_bookmarks.return_value = mock_bookmarks
        
        # Create args
        args = argparse.Namespace(
            input_file="input.html",
            output_file="output.csv",
            dry_run=False
        )
        
        # Convert
        convert_html(args)
        
        # Check that the functions were called with the correct arguments
        mock_read_file.assert_called_once_with("input.html")
        mock_parse_html.assert_called_once_with("html content")
        mock_extract_bookmarks.assert_called_once_with(mock_soup)
        mock_write_csv.assert_called_once_with("output.csv", mock_bookmarks, False)

    @patch("pocket.pocket2csv.read_html_file")
    @patch("pocket.pocket2csv.parse_html_content")
    @patch("pocket.pocket2csv.extract_bookmarks")
    @patch("pocket.pocket2csv.write_csv_file")
    def test_convert_html_no_bookmarks(self, mock_write_csv, mock_extract_bookmarks, mock_parse_html, mock_read_file):
        """Test that convert_html handles the case where no bookmarks are found."""
        # Set up mocks
        mock_read_file.return_value = "html content"
        mock_soup = MagicMock()
        mock_parse_html.return_value = mock_soup
        mock_extract_bookmarks.return_value = []
        
        # Create args
        args = argparse.Namespace(
            input_file="input.html",
            output_file="output.csv",
            dry_run=False
        )
        
        # Convert
        convert_html(args)
        
        # Check that write_csv_file was not called
        mock_write_csv.assert_not_called()

    @patch("pocket.pocket2csv.parse_command_line_args")
    @patch("pocket.pocket2csv.setup_logging")
    @patch("pocket.pocket2csv.get_logger")
    @patch("pocket.pocket2csv.convert_html")
    def test_main(self, mock_convert_html, mock_get_logger, mock_setup_logging, mock_parse_args):
        """Test that main correctly sets up the environment and calls convert_html."""
        # Set up mocks
        mock_args = argparse.Namespace(
            input_file="input.html",
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
        mock_convert_html.assert_called_once_with(mock_args)