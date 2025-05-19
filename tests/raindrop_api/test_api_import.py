"""
Tests for the raindrop_api.api_import module.
"""

import os
import sys
import pytest
import argparse
import tempfile
import json
from unittest.mock import patch, MagicMock, mock_open
from raindrop_api.api_import import (
    validate_api_token,
    validate_client_credentials,
    get_access_token,
    test_api_connection,
    get_collections,
    read_csv_file,
    convert_bookmark_to_raindrop,
    import_bookmarks,
    import_to_raindrop,
    main
)


class TestRaindropApiImport:
    """Tests for the raindrop_api.api_import module."""

    def setup_method(self):
        """Set up the test environment."""
        # Set up a logger mock
        self.logger_patcher = patch("raindrop_api.api_import.logger")
        self.mock_logger = self.logger_patcher.start()

        # Initialize the global logger variable
        import raindrop_api.api_import
        raindrop_api.api_import.logger = self.mock_logger

    def teardown_method(self):
        """Tear down the test environment."""
        self.logger_patcher.stop()

    def test_validate_api_token_valid(self):
        """Test that validate_api_token accepts valid tokens."""
        token = "valid_token_12345"
        result = validate_api_token(token)
        assert result == token

    def test_validate_api_token_invalid(self):
        """Test that validate_api_token rejects invalid tokens."""
        with pytest.raises(argparse.ArgumentTypeError):
            validate_api_token("")

        with pytest.raises(argparse.ArgumentTypeError):
            validate_api_token("short")

    def test_validate_client_credentials_valid(self):
        """Test that validate_client_credentials accepts valid credentials."""
        client_id = "valid_client_id_12345"
        client_secret = "valid_client_secret_12345"
        result_id, result_secret = validate_client_credentials(client_id, client_secret)
        assert result_id == client_id
        assert result_secret == client_secret

    def test_validate_client_credentials_invalid(self):
        """Test that validate_client_credentials rejects invalid credentials."""
        # Test invalid client ID
        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("", "valid_client_secret_12345")

        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("short", "valid_client_secret_12345")

        # Test invalid client secret
        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("valid_client_id_12345", "")

        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("valid_client_id_12345", "short")

    @patch("raindrop_api.api_import.requests.post")
    def test_get_access_token_success(self, mock_post):
        """Test that get_access_token returns an access token for successful requests."""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_access_token"}
        mock_post.return_value = mock_response

        result = get_access_token("valid_client_id", "valid_client_secret")
        assert result == "test_access_token"
        mock_post.assert_called_once()

        # Check that the request was made with the correct data
        args, kwargs = mock_post.call_args
        assert args[0] == "https://raindrop.io/oauth/access_token"
        assert kwargs["data"] == {
            "grant_type": "client_credentials",
            "client_id": "valid_client_id",
            "client_secret": "valid_client_secret"
        }

    @patch("raindrop_api.api_import.requests.post")
    def test_get_access_token_failure(self, mock_post):
        """Test that get_access_token raises an exception for failed requests."""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with pytest.raises(Exception):
            get_access_token("invalid_client_id", "invalid_client_secret")
        mock_post.assert_called_once()

    @patch("raindrop_api.api_import.requests.post")
    def test_get_access_token_missing_token(self, mock_post):
        """Test that get_access_token raises an exception if the response doesn't contain an access token."""
        # Mock a response with no access token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        with pytest.raises(Exception):
            get_access_token("valid_client_id", "valid_client_secret")
        mock_post.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_test_api_connection_success(self, mock_get):
        """Test that test_api_connection returns True for successful connections."""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": {"name": "Test User"}}
        mock_get.return_value = mock_response

        result = test_api_connection("valid_token")
        assert result is True
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_test_api_connection_failure(self, mock_get):
        """Test that test_api_connection returns False for failed connections."""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        result = test_api_connection("invalid_token")
        assert result is False
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_test_api_connection_exception(self, mock_get):
        """Test that test_api_connection handles exceptions."""
        # Mock an exception
        mock_get.side_effect = Exception("Connection error")

        result = test_api_connection("valid_token")
        assert result is False
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_get_collections_success(self, mock_get):
        """Test that get_collections returns collections for successful requests."""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"_id": 1, "title": "Test Collection"}]}
        mock_get.return_value = mock_response

        result = get_collections("valid_token")
        assert result == [{"_id": 1, "title": "Test Collection"}]
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_get_collections_failure(self, mock_get):
        """Test that get_collections returns an empty list for failed requests."""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        result = get_collections("invalid_token")
        assert result == []
        mock_get.assert_called_once()

    @patch("builtins.open", new_callable=mock_open, read_data='title,url,tags\n"Example","http://example.com","tag1,tag2"')
    def test_read_csv_file(self, mock_file):
        """Test that read_csv_file correctly reads a CSV file."""
        result = read_csv_file("input.csv")
        mock_file.assert_called_once_with("input.csv", "r")
        assert len(result) == 1
        assert result[0]["title"] == "Example"
        assert result[0]["url"] == "http://example.com"
        assert result[0]["tags"] == "tag1,tag2"

    @patch("builtins.open", side_effect=IOError("File not found"))
    def test_read_csv_file_error(self, mock_file):
        """Test that read_csv_file handles errors correctly."""
        with pytest.raises(IOError):
            read_csv_file("nonexistent.csv")

    def test_convert_bookmark_to_raindrop(self):
        """Test that convert_bookmark_to_raindrop correctly converts bookmarks."""
        bookmark = {
            "title": "Example",
            "url": "http://example.com",
            "tags": "tag1,tag2",
            "created": "2020-01-01 12:00:00"
        }

        with patch("raindrop_api.api_import.parser") as mock_parser:
            # Mock the date parser
            mock_date = MagicMock()
            mock_date.timestamp.return_value = 1577880000  # 2020-01-01 12:00:00 UTC
            mock_parser.parse.return_value = mock_date

            result = convert_bookmark_to_raindrop(bookmark, 1)

            assert result["link"] == "http://example.com"
            assert result["title"] == "Example"
            assert result["tags"] == ["tag1", "tag2"]
            assert result["collection"]["$id"] == 1
            assert result["created"] == 1577880000000  # Milliseconds

    def test_convert_bookmark_to_raindrop_no_tags(self):
        """Test that convert_bookmark_to_raindrop handles bookmarks without tags."""
        bookmark = {
            "title": "Example",
            "url": "http://example.com"
        }

        result = convert_bookmark_to_raindrop(bookmark, 1)

        assert result["link"] == "http://example.com"
        assert result["title"] == "Example"
        assert result["tags"] == []
        assert result["collection"]["$id"] == 1

    @patch("raindrop_api.api_import.requests.post")
    @patch("raindrop_api.api_import.tqdm")
    def test_import_bookmarks_success(self, mock_tqdm, mock_post):
        """Test that import_bookmarks correctly imports bookmarks."""
        # Mock the progress bar
        mock_progress_bar = MagicMock()
        mock_tqdm.return_value = mock_progress_bar

        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"_id": 1}, {"_id": 2}]}
        mock_post.return_value = mock_response

        # Create bookmarks
        bookmarks = [
            {"title": "Example 1", "url": "http://example.com", "tags": "tag1,tag2"},
            {"title": "Example 2", "url": "http://example.org", "tags": ""}
        ]

        # Import bookmarks
        result = import_bookmarks(bookmarks, "valid_token", 1, 50, False)

        # Check that the API was called
        mock_post.assert_called_once()

        # Check that the progress bar was updated
        assert mock_progress_bar.update.call_count == 2
        assert mock_progress_bar.close.call_count == 1

        # Check the result
        assert result == 2

    def test_import_bookmarks_dry_run(self):
        """Test that import_bookmarks in dry-run mode doesn't call the API."""
        # Create bookmarks
        bookmarks = [
            {"title": "Example 1", "url": "http://example.com", "tags": "tag1,tag2"},
            {"title": "Example 2", "url": "http://example.org", "tags": ""}
        ]

        # Import bookmarks in dry-run mode
        with patch("raindrop_api.api_import.requests.post") as mock_post:
            result = import_bookmarks(bookmarks, "valid_token", 1, 50, True)
            mock_post.assert_not_called()
            assert result == 2

    @patch("raindrop_api.api_import.validate_api_token")
    @patch("raindrop_api.api_import.test_api_connection")
    @patch("raindrop_api.api_import.validate_input_file")
    @patch("raindrop_api.api_import.read_csv_file")
    @patch("raindrop_api.api_import.import_bookmarks")
    def test_import_to_raindrop_with_api_token(self, mock_import_bookmarks, mock_read_csv, mock_validate_input, mock_test_connection, mock_validate_token):
        """Test that import_to_raindrop correctly orchestrates the import process with API token authentication."""
        # Set up mocks
        mock_validate_token.return_value = "valid_token"
        mock_test_connection.return_value = True
        mock_validate_input.return_value = "input.csv"
        mock_bookmarks = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_read_csv.return_value = mock_bookmarks
        mock_import_bookmarks.return_value = 2

        # Create args
        args = argparse.Namespace(
            api_token="valid_token",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False
        )

        # Import
        import_to_raindrop(args)

        # Check that the functions were called with the correct arguments
        mock_validate_token.assert_called_once_with("valid_token")
        mock_test_connection.assert_called_once_with("valid_token")
        mock_validate_input.assert_called_once_with("input.csv")
        mock_read_csv.assert_called_once_with("input.csv")
        mock_import_bookmarks.assert_called_once_with(mock_bookmarks, "valid_token", 1, 50, False)

    @patch("raindrop_api.api_import.validate_client_credentials")
    @patch("raindrop_api.api_import.get_access_token")
    @patch("raindrop_api.api_import.test_api_connection")
    @patch("raindrop_api.api_import.validate_input_file")
    @patch("raindrop_api.api_import.read_csv_file")
    @patch("raindrop_api.api_import.import_bookmarks")
    def test_import_to_raindrop_with_oauth(self, mock_import_bookmarks, mock_read_csv, mock_validate_input, mock_test_connection, mock_get_access_token, mock_validate_credentials):
        """Test that import_to_raindrop correctly orchestrates the import process with OAuth authentication."""
        # Set up mocks
        mock_validate_credentials.return_value = ("valid_client_id", "valid_client_secret")
        mock_get_access_token.return_value = "valid_access_token"
        mock_test_connection.return_value = True
        mock_validate_input.return_value = "input.csv"
        mock_bookmarks = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_read_csv.return_value = mock_bookmarks
        mock_import_bookmarks.return_value = 2

        # Create args
        args = argparse.Namespace(
            client_id="valid_client_id",
            client_secret="valid_client_secret",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False
        )

        # Import
        import_to_raindrop(args)

        # Check that the functions were called with the correct arguments
        mock_validate_credentials.assert_called_once_with("valid_client_id", "valid_client_secret")
        mock_get_access_token.assert_called_once_with("valid_client_id", "valid_client_secret")
        mock_test_connection.assert_called_once_with("valid_access_token")
        mock_validate_input.assert_called_once_with("input.csv")
        mock_read_csv.assert_called_once_with("input.csv")
        mock_import_bookmarks.assert_called_once_with(mock_bookmarks, "valid_access_token", 1, 50, False)

    @patch("raindrop_api.api_import.validate_api_token")
    @patch("raindrop_api.api_import.test_api_connection")
    def test_import_to_raindrop_connection_failure_with_api_token(self, mock_test_connection, mock_validate_token):
        """Test that import_to_raindrop handles API connection failures with API token authentication."""
        # Set up mocks
        mock_validate_token.return_value = "valid_token"
        mock_test_connection.return_value = False

        # Create args
        args = argparse.Namespace(
            api_token="valid_token",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False
        )

        # Import
        import_to_raindrop(args)

        # Check that the functions were called with the correct arguments
        mock_validate_token.assert_called_once_with("valid_token")
        mock_test_connection.assert_called_once_with("valid_token")

        # Check that the error was logged
        self.mock_logger.error.assert_called_once()

    @patch("raindrop_api.api_import.validate_client_credentials")
    @patch("raindrop_api.api_import.get_access_token")
    @patch("raindrop_api.api_import.test_api_connection")
    def test_import_to_raindrop_connection_failure_with_oauth(self, mock_test_connection, mock_get_access_token, mock_validate_credentials):
        """Test that import_to_raindrop handles API connection failures with OAuth authentication."""
        # Set up mocks
        mock_validate_credentials.return_value = ("valid_client_id", "valid_client_secret")
        mock_get_access_token.return_value = "valid_access_token"
        mock_test_connection.return_value = False

        # Create args
        args = argparse.Namespace(
            client_id="valid_client_id",
            client_secret="valid_client_secret",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False
        )

        # Import
        import_to_raindrop(args)

        # Check that the functions were called with the correct arguments
        mock_validate_credentials.assert_called_once_with("valid_client_id", "valid_client_secret")
        mock_get_access_token.assert_called_once_with("valid_client_id", "valid_client_secret")
        mock_test_connection.assert_called_once_with("valid_access_token")

        # Check that the error was logged
        self.mock_logger.error.assert_called_once()

    @patch("raindrop_api.api_import.validate_client_credentials")
    @patch("raindrop_api.api_import.get_access_token")
    def test_import_to_raindrop_oauth_failure(self, mock_get_access_token, mock_validate_credentials):
        """Test that import_to_raindrop handles OAuth authentication failures."""
        # Set up mocks
        mock_validate_credentials.return_value = ("valid_client_id", "valid_client_secret")
        mock_get_access_token.side_effect = Exception("Failed to get access token")

        # Create args
        args = argparse.Namespace(
            client_id="valid_client_id",
            client_secret="valid_client_secret",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False
        )

        # Import
        import_to_raindrop(args)

        # Check that the functions were called with the correct arguments
        mock_validate_credentials.assert_called_once_with("valid_client_id", "valid_client_secret")
        mock_get_access_token.assert_called_once_with("valid_client_id", "valid_client_secret")

        # Check that the error was logged
        self.mock_logger.error.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("raindrop_api.api_import.setup_logging")
    @patch("raindrop_api.api_import.get_logger")
    @patch("raindrop_api.api_import.import_to_raindrop")
    def test_main_with_api_token(self, mock_import_to_raindrop, mock_get_logger, mock_setup_logging, mock_parse_args):
        """Test that main correctly sets up the environment and calls import_to_raindrop with API token authentication."""
        # Set up mocks
        mock_args = argparse.Namespace(
            api_token="valid_token",
            client_id=None,
            client_secret=None,
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            log_file="log.txt",
            dry_run=False
        )
        mock_parse_args.return_value = mock_args
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call main
        main()

        # Check that the functions were called with the correct arguments
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with("log.txt")
        mock_get_logger.assert_called_once()
        mock_import_to_raindrop.assert_called_once_with(mock_args)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("raindrop_api.api_import.setup_logging")
    @patch("raindrop_api.api_import.get_logger")
    @patch("raindrop_api.api_import.import_to_raindrop")
    def test_main_with_oauth(self, mock_import_to_raindrop, mock_get_logger, mock_setup_logging, mock_parse_args):
        """Test that main correctly sets up the environment and calls import_to_raindrop with OAuth authentication."""
        # Set up mocks
        mock_args = argparse.Namespace(
            api_token=None,
            client_id="valid_client_id",
            client_secret="valid_client_secret",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            log_file="log.txt",
            dry_run=False
        )
        mock_parse_args.return_value = mock_args
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call main
        main()

        # Check that the functions were called with the correct arguments
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with("log.txt")
        mock_get_logger.assert_called_once()
        mock_import_to_raindrop.assert_called_once_with(mock_args)
