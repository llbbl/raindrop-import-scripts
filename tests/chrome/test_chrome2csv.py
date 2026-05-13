import argparse
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

from chrome.chrome2csv import (
    ChromeBookmark,
    ChromeBookmarkConverter,
    convert_json,
    main,
    parse_command_line_args,
)


class TestChromeBookmark:
    """Tests for the ChromeBookmark class."""

    def test_chrome_bookmark_creation(self):
        """Test that ChromeBookmark objects are created correctly."""
        bookmark = ChromeBookmark(
            title="Example",
            url="http://example.com",
            created="01/01/2020 00:00:00",
            tags="Folder1,Folder2",
        )
        assert bookmark.title == "Example"
        assert bookmark.url == "http://example.com"
        assert bookmark.created == "01/01/2020 00:00:00"
        assert bookmark.tags == "Folder1,Folder2"

    def test_chrome_bookmark_to_dict(self):
        """Test that ChromeBookmark.to_dict() returns the correct dictionary."""
        bookmark = ChromeBookmark(
            title="Example",
            url="http://example.com",
            created="01/01/2020 00:00:00",
            tags="Folder1,Folder2",
        )
        expected = {
            "title": "Example",
            "url": "http://example.com",
            "created": "01/01/2020 00:00:00",
            "tags": "Folder1,Folder2",
        }
        assert bookmark.to_dict() == expected


class TestChromeBookmarkConverter:
    """Tests for the ChromeBookmarkConverter class."""

    def setup_method(self):
        """Set up the test environment."""
        # Inject a mock logger directly so node-processing works without main() being called.
        self.mock_logger = MagicMock()
        self.converter = ChromeBookmarkConverter(
            "input.json", "output.csv", logger=self.mock_logger
        )

    @patch("builtins.open", new_callable=mock_open, read_data='{"roots": {}}')
    def test_read_json_file(self, mock_file):
        """Test that read_json_file correctly reads a file."""
        content = self.converter.read_json_file()
        mock_file.assert_called_once_with("input.json", encoding="utf-8")
        assert content == {"roots": {}}

    @patch("builtins.open", side_effect=OSError("File not found"))
    def test_read_json_file_error(self, mock_file):
        """Test that read_json_file handles errors correctly."""
        with pytest.raises(IOError):
            self.converter.read_json_file()

    def test_process_bookmark_node_url(self):
        """Test that process_bookmark_node correctly processes a URL node."""
        node_data = {
            "type": "url",
            "name": "Example",
            "url": "http://example.com",
            "date_added": "13245909254590000",
        }
        bookmarks = self.converter.process_bookmark_node(node_data, ["Folder1", "Folder2"])

        assert len(bookmarks) == 1
        assert isinstance(bookmarks[0], ChromeBookmark)
        assert bookmarks[0].title == "Example"
        assert bookmarks[0].url == "http://example.com"
        assert bookmarks[0].tags == "Folder1,Folder2"

    def test_process_bookmark_node_folder(self):
        """Test that process_bookmark_node correctly processes a folder node."""
        node_data = {
            "type": "folder",
            "name": "Folder3",
            "children": [
                {
                    "type": "url",
                    "name": "Example 1",
                    "url": "http://example1.com",
                    "date_added": "13245909254590000",
                },
                {
                    "type": "url",
                    "name": "Example 2",
                    "url": "http://example2.com",
                    "date_added": "13245909254590000",
                },
            ],
        }
        bookmarks = self.converter.process_bookmark_node(node_data, ["Folder1", "Folder2"])

        assert len(bookmarks) == 2
        assert all(isinstance(b, ChromeBookmark) for b in bookmarks)
        assert bookmarks[0].title == "Example 1"
        assert bookmarks[0].tags == "Folder1,Folder2,Folder3"
        assert bookmarks[1].title == "Example 2"
        assert bookmarks[1].tags == "Folder1,Folder2,Folder3"

    def test_process_bookmark_node_without_main_logger(self):
        """Regression: node processing must work without main() having been called.

        Earlier refactor had BookmarkNode reference a module-level logger that was
        None until main() ran. Ensure no NoneType crash on the bad-timestamp warning
        path when only the instance logger is configured.
        """
        bad_node = {
            "type": "url",
            "name": "Bad Timestamp",
            "url": "http://example.com",
            "date_added": "not-a-number",
        }
        # Should not raise even though module-level logger has not been initialised
        bookmarks = self.converter.process_bookmark_node(bad_node, [])
        assert len(bookmarks) == 1
        self.mock_logger.warning.assert_called()

    def test_extract_bookmarks(self):
        """Test that extract_bookmarks correctly extracts bookmarks from Chrome JSON."""
        data = {
            "roots": {
                "bookmark_bar": {
                    "type": "folder",
                    "name": "Bookmarks Bar",
                    "children": [
                        {
                            "type": "url",
                            "name": "Example 1",
                            "url": "http://example1.com",
                            "date_added": "13245909254590000",
                        }
                    ],
                },
                "other": {
                    "type": "folder",
                    "name": "Other Bookmarks",
                    "children": [
                        {
                            "type": "url",
                            "name": "Example 2",
                            "url": "http://example2.com",
                            "date_added": "13245909254590000",
                        }
                    ],
                },
            }
        }

        bookmarks = self.converter.extract_bookmarks(data)
        assert len(bookmarks) == 2
        assert all(isinstance(b, ChromeBookmark) for b in bookmarks)
        titles = [b.title for b in bookmarks]
        assert "Example 1" in titles
        assert "Example 2" in titles

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_write_csv_file(self, mock_dict_writer, mock_file):
        """Test that write_csv_file correctly writes records to a CSV file."""
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer

        bookmarks = [
            ChromeBookmark(
                title="Example 1",
                url="http://example1.com",
                created="01/01/2020 00:00:00",
                tags="Folder1,Folder2",
            ),
            ChromeBookmark(
                title="Example 2",
                url="http://example2.com",
                created="01/01/2020 00:00:00",
                tags="Folder3",
            ),
        ]

        self.converter.write_csv_file(bookmarks)
        mock_file.assert_called_once_with("output.csv", "w", encoding="utf-8", newline="")
        mock_dict_writer.assert_called_once()
        assert list(mock_dict_writer.call_args[1]["fieldnames"]) == [
            "title",
            "url",
            "created",
            "tags",
        ]
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerow.assert_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.DictWriter")
    def test_write_csv_file_uses_quote_all(self, mock_dict_writer, mock_file):
        """Test that write_csv_file configures DictWriter with QUOTE_ALL semantics."""
        import csv as csv_module

        mock_dict_writer.return_value = MagicMock()
        bookmarks = [
            ChromeBookmark(
                title="Example",
                url="http://example.com",
                created="01/01/2020 00:00:00",
                tags="Folder1",
            )
        ]

        self.converter.write_csv_file(bookmarks)
        kwargs = mock_dict_writer.call_args.kwargs
        assert kwargs["quoting"] == csv_module.QUOTE_ALL
        assert kwargs["delimiter"] == ","
        assert kwargs["lineterminator"] == "\n"
        assert kwargs["quotechar"] == '"'

    def test_write_csv_file_dry_run(self):
        """Test that write_csv_file in dry-run mode doesn't write to a file."""
        bookmarks = [
            ChromeBookmark(
                title="Example 1",
                url="http://example1.com",
                created="01/01/2020 00:00:00",
                tags="Folder1,Folder2",
            )
        ]
        with patch("builtins.open") as mock_open_:
            self.converter.write_csv_file(bookmarks, dry_run=True)
            mock_open_.assert_not_called()

    def test_write_csv_file_applies_field_mappings(self):
        """write_csv_file should call map_rows when field_mappings is provided."""
        bookmarks = [
            ChromeBookmark(
                title="Example",
                url="http://example.com",
                created="01/01/2020 00:00:00",
                tags="Folder1",
            )
        ]
        field_mappings = {"title": "renamed_title", "url": "renamed_url"}

        with (
            patch("chrome.chrome2csv.map_rows") as mock_map_rows,
            patch("builtins.open", new_callable=mock_open),
            patch("csv.DictWriter") as mock_dict_writer,
        ):
            mock_map_rows.return_value = [
                {"renamed_title": "Example", "renamed_url": "http://example.com"}
            ]
            mock_dict_writer.return_value = MagicMock()
            self.converter.write_csv_file(bookmarks, field_mappings=field_mappings)

            mock_map_rows.assert_called_once()
            # Honor the mapped output as the writer's fieldnames
            assert list(mock_dict_writer.call_args.kwargs["fieldnames"]) == [
                "renamed_title",
                "renamed_url",
            ]

    def test_write_csv_file_preview_mode(self):
        """write_csv_file should invoke preview_items with the configured limit."""
        bookmarks = [
            ChromeBookmark(
                title="Example",
                url="http://example.com",
                created="01/01/2020 00:00:00",
                tags="",
            )
        ]
        with (
            patch("chrome.chrome2csv.preview_items") as mock_preview,
            patch("builtins.open", new_callable=mock_open),
            patch("csv.DictWriter"),
        ):
            self.converter.write_csv_file(bookmarks, preview=True, preview_limit=5)
            mock_preview.assert_called_once()
            assert mock_preview.call_args.kwargs["limit"] == 5

    @patch("chrome.chrome2csv.ChromeBookmarkConverter.read_json_file")
    @patch("chrome.chrome2csv.ChromeBookmarkConverter.extract_bookmarks")
    @patch("chrome.chrome2csv.ChromeBookmarkConverter.write_csv_file")
    def test_convert(self, mock_write_csv, mock_extract_bookmarks, mock_read_file):
        """Test that convert correctly orchestrates the conversion process."""
        mock_read_file.return_value = {"roots": {}}
        mock_bookmarks = [
            ChromeBookmark(
                title="Example 1",
                url="http://example1.com",
                created="01/01/2020 00:00:00",
                tags="Folder1",
            )
        ]
        mock_extract_bookmarks.return_value = mock_bookmarks

        self.converter.convert()
        mock_read_file.assert_called_once()
        mock_extract_bookmarks.assert_called_once_with({"roots": {}})
        mock_write_csv.assert_called_once_with(
            mock_bookmarks,
            field_mappings=None,
            preview=False,
            preview_limit=10,
            dry_run=False,
        )


class TestChrome2Csv:
    """Tests for the chrome2csv module-level functions."""

    @patch("argparse.ArgumentParser")
    def test_parse_command_line_args(self, mock_arg_parser):
        """Test that parse_command_line_args correctly parses arguments."""
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = argparse.Namespace(input_file="input.json", output_file="output.csv")
        mock_parser.parse_args.return_value = mock_args

        args = parse_command_line_args(
            ["--input-file", "input.json", "--output-file", "output.csv"]
        )

        assert args.input_file == "input.json"
        assert args.output_file == "output.csv"

    @patch("chrome.chrome2csv.apply_field_mappings")
    @patch("chrome.chrome2csv.ChromeBookmarkConverter")
    def test_convert_json(self, mock_converter_class, mock_apply_field_mappings):
        """Test that convert_json correctly creates and uses the converter."""
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        mock_apply_field_mappings.return_value = {"title": "title"}

        args = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
            dry_run=False,
            preview=True,
            preview_limit=7,
        )

        convert_json(args)
        mock_converter_class.assert_called_once_with("input.json", "output.csv")
        mock_apply_field_mappings.assert_called_once_with(args)
        mock_converter.convert.assert_called_once_with(
            field_mappings={"title": "title"},
            preview=True,
            preview_limit=7,
            dry_run=False,
        )

    @patch("chrome.chrome2csv.apply_field_mappings")
    @patch("chrome.chrome2csv.ChromeBookmarkConverter")
    def test_convert_json_defensive_arg_access(
        self, mock_converter_class, mock_apply_field_mappings
    ):
        """convert_json should not crash when optional args (e.g. dry_run) are missing."""
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        mock_apply_field_mappings.return_value = {}

        # Namespace missing dry_run/preview/preview_limit
        args = argparse.Namespace(input_file="input.json", output_file="output.csv")
        convert_json(args)
        mock_converter.convert.assert_called_once_with(
            field_mappings={},
            preview=False,
            preview_limit=10,
            dry_run=False,
        )

    @patch("chrome.chrome2csv.convert_json")
    @patch("chrome.chrome2csv.get_logger")
    @patch("chrome.chrome2csv.setup_logging")
    @patch("chrome.chrome2csv.parse_command_line_args")
    def test_main(
        self,
        mock_parse_args,
        mock_setup_logging,
        mock_get_logger,
        mock_convert_json,
    ):
        """Test that main parses args first, then configures logging, then converts."""
        mock_args = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
            log_file="run.log",
        )
        mock_parse_args.return_value = mock_args

        main()

        mock_parse_args.assert_called_once_with(sys.argv[1:])
        mock_setup_logging.assert_called_once_with("run.log")
        mock_get_logger.assert_called_once()
        mock_convert_json.assert_called_once_with(mock_args)

    @patch("chrome.chrome2csv.convert_json")
    @patch("chrome.chrome2csv.get_logger")
    @patch("chrome.chrome2csv.setup_logging")
    @patch("chrome.chrome2csv.parse_command_line_args")
    def test_main_forwards_log_file(
        self,
        mock_parse_args,
        mock_setup_logging,
        mock_get_logger,
        mock_convert_json,
    ):
        """The --log-file argument must be forwarded to setup_logging."""
        mock_parse_args.return_value = argparse.Namespace(
            input_file="input.json",
            output_file="output.csv",
            log_file="/tmp/chrome.log",
        )
        main()
        mock_setup_logging.assert_called_once_with("/tmp/chrome.log")
