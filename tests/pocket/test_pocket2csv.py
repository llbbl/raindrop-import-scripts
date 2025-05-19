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
    main,
    PocketConverter
)


class TestPocket2Csv:
    """Tests for the pocket2csv module's procedural functions."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("pocket.pocket2csv.logger")
        self.mock_logger = self.logger_patcher.start()

        # Initialize the global logger variable
        import pocket.pocket2csv
        pocket.pocket2csv.logger = self.mock_logger

    def teardown_method(self):
        """Tear down the test environment."""
        self.logger_patcher.stop()

    @patch("argparse.ArgumentParser")
    def test_parse_command_line_args(self, mock_arg_parser):
        """Test that parse_command_line_args correctly parses arguments."""
        # Set up mocks
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = argparse.Namespace(input_file="input.html", output_file="output.csv")
        mock_parser.parse_args.return_value = mock_args

        # Test with valid arguments
        args = parse_command_line_args([
            "--input-file", "input.html",
            "--output-file", "output.csv"
        ])

        # Check that the returned args are correct
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

    def test_parse_html_content(self):
        """Test that parse_html_content correctly parses HTML content."""
        with patch("pocket.pocket2csv.BeautifulSoup") as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup

            result = parse_html_content("test content")
            mock_bs.assert_called_once_with("test content", "html.parser")
            assert result == mock_soup

    def test_extract_bookmarks(self):
        """Test that extract_bookmarks correctly extracts bookmarks."""
        # Create a mock progress bar
        with patch("pocket.pocket2csv.tqdm") as mock_tqdm:
            mock_progress_bar = MagicMock()
            mock_tqdm.return_value = mock_progress_bar

            # Create a mock soup with bookmarks
            soup = MagicMock()

            # Create mock anchor tags
            anchor1 = MagicMock()
            anchor1.get.side_effect = lambda attr: {
                "href": "http://example.com",
                "time_added": "1577836800",
                "tags": "tag1,tag2"
            }.get(attr)
            anchor1.string = "Example 1"

            anchor2 = MagicMock()
            anchor2.get.side_effect = lambda attr: {
                "href": "http://example.org",
                "time_added": "1580515200",
                "tags": None
            }.get(attr)
            anchor2.string = "Example 2"

            # Create mock bookmarks with find method that returns the mock anchors
            bookmark1 = MagicMock()
            bookmark1.find.return_value = anchor1

            bookmark2 = MagicMock()
            bookmark2.find.return_value = anchor2

            soup.find_all.return_value = [bookmark1, bookmark2]

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

    def test_extract_bookmarks_with_errors(self):
        """Test that extract_bookmarks handles errors correctly."""
        # Create a mock progress bar
        with patch("pocket.pocket2csv.tqdm") as mock_tqdm:
            mock_progress_bar = MagicMock()
            mock_tqdm.return_value = mock_progress_bar

            # Create a mock soup with a malformed bookmark
            soup = MagicMock()

            # Create mock anchor tag with invalid time_added
            anchor = MagicMock()
            anchor.get.side_effect = lambda attr: {
                "href": "http://example.com",
                "time_added": "invalid",  # This will cause a ValueError when converted to float
                "tags": None
            }.get(attr)
            anchor.string = "Example 1"

            # Create mock bookmark with find method that returns the mock anchor
            bookmark = MagicMock()
            bookmark.find.return_value = anchor

            soup.find_all.return_value = [bookmark]

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


class TestPocketConverter:
    """Tests for the PocketConverter class."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_mock = MagicMock()
        self.converter = PocketConverter(self.logger_mock)

    def test_init(self):
        """Test that the PocketConverter initializes correctly."""
        assert self.converter.logger == self.logger_mock

    @patch("argparse.ArgumentParser")
    def test_parse_command_line_args(self, mock_arg_parser):
        """Test that parse_command_line_args correctly parses arguments."""
        # Set up mocks
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = argparse.Namespace(input_file="input.html", output_file="output.csv")
        mock_parser.parse_args.return_value = mock_args

        # Test with valid arguments
        args = self.converter.parse_command_line_args([
            "--input-file", "input.html",
            "--output-file", "output.csv"
        ])

        # Check that the returned args are correct
        assert args.input_file == "input.html"
        assert args.output_file == "output.csv"

    @patch("builtins.open", new_callable=mock_open, read_data="test content")
    def test_read_html_file(self, mock_file):
        """Test that read_html_file correctly reads a file."""
        content = self.converter.read_html_file("input.html")
        mock_file.assert_called_once_with("input.html", "r")
        assert content == "test content"

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_html_file_error(self, mock_file):
        """Test that read_html_file handles errors correctly."""
        with pytest.raises(IOError):
            self.converter.read_html_file("nonexistent.html")

    def test_parse_html_content(self):
        """Test that parse_html_content correctly parses HTML content."""
        with patch("bs4.BeautifulSoup") as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup

            result = self.converter.parse_html_content("test content")
            mock_bs.assert_called_once_with("test content", "html.parser")
            assert result == mock_soup

    def test_extract_bookmarks(self):
        """Test that extract_bookmarks correctly extracts bookmarks."""
        # Create a mock progress bar
        with patch("pocket.pocket2csv.tqdm") as mock_tqdm:
            mock_progress_bar = MagicMock()
            mock_tqdm.return_value = mock_progress_bar

            # Create a mock soup with bookmarks
            soup = MagicMock()

            # Create mock anchor tags
            anchor1 = MagicMock()
            anchor1.get.side_effect = lambda attr: {
                "href": "http://example.com",
                "time_added": "1577836800",
                "tags": "tag1,tag2"
            }.get(attr)
            anchor1.string = "Example 1"

            anchor2 = MagicMock()
            anchor2.get.side_effect = lambda attr: {
                "href": "http://example.org",
                "time_added": "1580515200",
                "tags": None
            }.get(attr)
            anchor2.string = "Example 2"

            # Create mock bookmarks with find method that returns the mock anchors
            bookmark1 = MagicMock()
            bookmark1.find.return_value = anchor1

            bookmark2 = MagicMock()
            bookmark2.find.return_value = anchor2

            soup.find_all.return_value = [bookmark1, bookmark2]

            # Extract bookmarks
            bookmarks = self.converter.extract_bookmarks(soup)
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
        self.converter.write_csv_file("output.csv", records)

        # Check that the file was opened
        mock_file.assert_called_once_with("output.csv", "w")

        # Check that the writer was created with the correct fieldnames
        mock_dict_writer.assert_called_once()
        assert mock_dict_writer.call_args[1]["fieldnames"] == ["title", "url", "tags"]

        # Check that the header and rows were written
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once_with(records)

    @patch("pocket.pocket2csv.PocketConverter.read_html_file")
    @patch("pocket.pocket2csv.PocketConverter.parse_html_content")
    @patch("pocket.pocket2csv.PocketConverter.extract_bookmarks")
    @patch("pocket.pocket2csv.PocketConverter.write_csv_file")
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
        self.converter.convert_html(args)

        # Check that the functions were called with the correct arguments
        mock_read_file.assert_called_once_with("input.html")
        mock_parse_html.assert_called_once_with("html content")
        mock_extract_bookmarks.assert_called_once_with(
            mock_soup, 
            filter_tag=None, 
            filter_date_from=None, 
            filter_date_to=None, 
            filter_title=None, 
            filter_url=None
        )
        mock_write_csv.assert_called_once()

    @patch("pocket.pocket2csv.PocketConverter.parse_command_line_args")
    @patch("pocket.pocket2csv.PocketConverter.convert_html")
    def test_run(self, mock_convert_html, mock_parse_args):
        """Test that run correctly parses arguments and calls convert_html."""
        # Set up mocks
        mock_args = argparse.Namespace(
            input_file="input.html",
            output_file="output.csv"
        )
        mock_parse_args.return_value = mock_args

        # Run
        self.converter.run(["--input-file", "input.html", "--output-file", "output.csv"])

        # Check that the functions were called with the correct arguments
        mock_parse_args.assert_called_once_with(["--input-file", "input.html", "--output-file", "output.csv"])
        mock_convert_html.assert_called_once_with(mock_args)
