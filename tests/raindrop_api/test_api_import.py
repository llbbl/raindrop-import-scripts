"""
Tests for the raindrop_api.api_import module.
"""

import argparse
from unittest.mock import MagicMock, mock_open, patch

import pytest

from raindrop_api.api_import import (
    RaindropApiImporter,
    import_to_raindrop,
    main,
    validate_api_token,
    validate_client_credentials,
)


def _make_importer(
    *,
    input_file: str = "input.csv",
    collection_id: int = 1,
    batch_size: int = 50,
    api_token: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> tuple[RaindropApiImporter, MagicMock]:
    """Build a RaindropApiImporter with an injected mock logger."""
    mock_logger = MagicMock()
    importer = RaindropApiImporter(
        input_file=input_file,
        collection_id=collection_id,
        batch_size=batch_size,
        api_token=api_token,
        client_id=client_id,
        client_secret=client_secret,
        logger=mock_logger,
    )
    return importer, mock_logger


class TestModuleLevelValidators:
    """Tests for module-level validator helpers."""

    def test_validate_api_token_valid(self):
        token = "valid_token_12345"
        assert validate_api_token(token) == token

    def test_validate_api_token_invalid(self):
        with pytest.raises(argparse.ArgumentTypeError):
            validate_api_token("")
        with pytest.raises(argparse.ArgumentTypeError):
            validate_api_token("short")

    def test_validate_client_credentials_valid(self):
        cid = "valid_client_id_12345"
        secret = "valid_client_secret_12345"
        result_id, result_secret = validate_client_credentials(cid, secret)
        assert result_id == cid
        assert result_secret == secret

    def test_validate_client_credentials_invalid(self):
        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("", "valid_client_secret_12345")
        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("short", "valid_client_secret_12345")
        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("valid_client_id_12345", "")
        with pytest.raises(argparse.ArgumentTypeError):
            validate_client_credentials("valid_client_id_12345", "short")


class TestRaindropApiImporter:
    """Tests for the RaindropApiImporter class."""

    @patch("raindrop_api.api_import.requests.post")
    def test_get_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_access_token"}
        mock_post.return_value = mock_response

        importer, _ = _make_importer(
            client_id="valid_client_id", client_secret="valid_client_secret"
        )
        result = importer.get_access_token()
        assert result == "test_access_token"
        mock_post.assert_called_once()

        args, kwargs = mock_post.call_args
        assert args[0] == "https://raindrop.io/oauth/access_token"
        assert kwargs["data"] == {
            "grant_type": "client_credentials",
            "client_id": "valid_client_id",
            "client_secret": "valid_client_secret",
        }

    @patch("raindrop_api.api_import.requests.post")
    def test_get_access_token_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        importer, _ = _make_importer(
            client_id="invalid_client_id", client_secret="invalid_client_secret"
        )
        with pytest.raises(Exception, match="Failed to get access token"):
            importer.get_access_token()
        mock_post.assert_called_once()

    @patch("raindrop_api.api_import.requests.post")
    def test_get_access_token_missing_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        importer, _ = _make_importer(
            client_id="valid_client_id", client_secret="valid_client_secret"
        )
        with pytest.raises(Exception, match="No access token in response"):
            importer.get_access_token()
        mock_post.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_check_api_connection_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": {"name": "Test User"}}
        mock_get.return_value = mock_response

        importer, _ = _make_importer()
        assert importer.check_api_connection("valid_token") is True
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_check_api_connection_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        importer, _ = _make_importer()
        assert importer.check_api_connection("invalid_token") is False
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_check_api_connection_exception(self, mock_get):
        mock_get.side_effect = Exception("Connection error")

        importer, _ = _make_importer()
        assert importer.check_api_connection("valid_token") is False
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_get_collections_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"_id": 1, "title": "Test Collection"}]}
        mock_get.return_value = mock_response

        importer, _ = _make_importer()
        result = importer.get_collections("valid_token")
        assert result == [{"_id": 1, "title": "Test Collection"}]
        mock_get.assert_called_once()

    @patch("raindrop_api.api_import.requests.get")
    def test_get_collections_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        importer, _ = _make_importer()
        result = importer.get_collections("invalid_token")
        assert result == []
        mock_get.assert_called_once()

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='title,url,tags\n"Example","http://example.com","tag1,tag2"',
    )
    def test_read_csv(self, mock_file):
        importer, _ = _make_importer(input_file="input.csv")
        result = importer.read_csv()
        mock_file.assert_called_once_with("input.csv")
        assert len(result) == 1
        assert result[0]["title"] == "Example"
        assert result[0]["url"] == "http://example.com"
        assert result[0]["tags"] == "tag1,tag2"

    @patch("builtins.open", side_effect=OSError("File not found"))
    def test_read_csv_error(self, mock_file):
        importer, _ = _make_importer(input_file="nonexistent.csv")
        with pytest.raises(OSError):
            importer.read_csv()

    def test_convert_bookmark_to_raindrop(self):
        bookmark = {
            "title": "Example",
            "url": "http://example.com",
            "tags": "tag1,tag2",
            "created": "2020-01-01 12:00:00",
        }

        importer, _ = _make_importer(collection_id=1)
        with patch("dateutil.parser.parse") as mock_parse:
            mock_date = MagicMock()
            mock_date.timestamp.return_value = 1577880000
            mock_parse.return_value = mock_date

            result = importer.convert_bookmark_to_raindrop(bookmark)

            assert result["link"] == "http://example.com"
            assert result["title"] == "Example"
            assert result["tags"] == ["tag1", "tag2"]
            assert result["collection"]["$id"] == 1
            assert result["created"] == 1577880000000

    def test_convert_bookmark_to_raindrop_no_tags(self):
        bookmark = {"title": "Example", "url": "http://example.com"}

        importer, _ = _make_importer(collection_id=1)
        result = importer.convert_bookmark_to_raindrop(bookmark)

        assert result["link"] == "http://example.com"
        assert result["title"] == "Example"
        assert result["tags"] == []
        assert result["collection"]["$id"] == 1

    def test_convert_bookmark_to_raindrop_bad_date_logs_warning(self):
        importer, mock_logger = _make_importer(collection_id=1)
        bookmark = {"title": "X", "url": "http://x", "created": "not-a-date"}
        result = importer.convert_bookmark_to_raindrop(bookmark)
        # No "created" key should be present when parsing fails
        assert "created" not in result
        mock_logger.warning.assert_called_once()

    @patch("raindrop_api.api_import.requests.post")
    @patch("raindrop_api.api_import.tqdm")
    def test_import_bookmarks_success(self, mock_tqdm, mock_post):
        mock_progress_bar = MagicMock()
        mock_tqdm.return_value = mock_progress_bar

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"_id": 1}, {"_id": 2}]}
        mock_post.return_value = mock_response

        bookmarks = [
            {"title": "Example 1", "url": "http://example.com", "tags": "tag1,tag2"},
            {"title": "Example 2", "url": "http://example.org", "tags": ""},
        ]

        importer, _ = _make_importer(collection_id=1, batch_size=50)
        # Patch time.sleep to avoid the rate-limit delay during the test.
        with patch("raindrop_api.api_import.time.sleep"):
            result = importer.import_bookmarks(bookmarks, "valid_token", dry_run=False)

        mock_post.assert_called_once()
        mock_progress_bar.update.assert_called_once_with(2)
        assert mock_progress_bar.close.call_count == 1
        assert result == 2

    def test_import_bookmarks_dry_run(self):
        bookmarks = [
            {"title": "Example 1", "url": "http://example.com", "tags": "tag1,tag2"},
            {"title": "Example 2", "url": "http://example.org", "tags": ""},
        ]

        importer, _ = _make_importer(collection_id=1, batch_size=50)
        with patch("raindrop_api.api_import.requests.post") as mock_post:
            result = importer.import_bookmarks(bookmarks, "valid_token", dry_run=True)
            mock_post.assert_not_called()
            assert result == 2

    def test_import_bookmarks_empty(self):
        importer, mock_logger = _make_importer()
        assert importer.import_bookmarks([], "tok", dry_run=False) == 0
        mock_logger.warning.assert_called_once()

    def test_authenticate_with_api_token(self):
        importer, mock_logger = _make_importer(api_token="valid_token_12345")
        token = importer.authenticate()
        assert token == "valid_token_12345"
        mock_logger.warning.assert_called_once()

    def test_authenticate_no_credentials(self):
        importer, mock_logger = _make_importer()
        assert importer.authenticate() is None
        mock_logger.error.assert_called_once()

    @patch.object(RaindropApiImporter, "get_access_token")
    def test_authenticate_oauth_success(self, mock_get_token):
        mock_get_token.return_value = "access_token_value"
        importer, _ = _make_importer(
            client_id="valid_client_id_12345",
            client_secret="valid_client_secret_12345",
        )
        assert importer.authenticate() == "access_token_value"

    @patch.object(RaindropApiImporter, "get_access_token")
    def test_authenticate_oauth_failure_falls_back_to_token(self, mock_get_token):
        mock_get_token.side_effect = Exception("oauth boom")
        importer, _ = _make_importer(
            client_id="valid_client_id_12345",
            client_secret="valid_client_secret_12345",
            api_token="fallback_token_12345",
        )
        assert importer.authenticate() == "fallback_token_12345"

    @patch.object(RaindropApiImporter, "get_access_token")
    def test_authenticate_oauth_failure_no_fallback(self, mock_get_token):
        mock_get_token.side_effect = Exception("oauth boom")
        importer, mock_logger = _make_importer(
            client_id="valid_client_id_12345",
            client_secret="valid_client_secret_12345",
        )
        assert importer.authenticate() is None
        # Two errors: the OAuth failure, and the no-fallback message.
        assert mock_logger.error.call_count == 2


class TestImportToRaindropShim:
    """Tests for the procedural import_to_raindrop shim and main()."""

    @patch("raindrop_api.api_import.validate_input_file")
    @patch.object(RaindropApiImporter, "check_api_connection")
    @patch.object(RaindropApiImporter, "read_csv")
    @patch.object(RaindropApiImporter, "import_bookmarks")
    def test_import_to_raindrop_with_api_token(
        self,
        mock_import_bookmarks,
        mock_read_csv,
        mock_check_connection,
        mock_validate_input,
    ):
        mock_check_connection.return_value = True
        mock_validate_input.return_value = "input.csv"
        mock_read_csv.return_value = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_import_bookmarks.return_value = 2

        args = argparse.Namespace(
            api_token="valid_token_12345",
            client_id=None,
            client_secret=None,
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False,
        )

        import_to_raindrop(args)

        mock_validate_input.assert_called_once_with("input.csv")
        mock_check_connection.assert_called_once_with("valid_token_12345")
        mock_read_csv.assert_called_once()
        mock_import_bookmarks.assert_called_once()

    @patch("raindrop_api.api_import.validate_input_file")
    @patch.object(RaindropApiImporter, "get_access_token")
    @patch.object(RaindropApiImporter, "check_api_connection")
    @patch.object(RaindropApiImporter, "read_csv")
    @patch.object(RaindropApiImporter, "import_bookmarks")
    def test_import_to_raindrop_with_oauth(
        self,
        mock_import_bookmarks,
        mock_read_csv,
        mock_check_connection,
        mock_get_access_token,
        mock_validate_input,
    ):
        mock_get_access_token.return_value = "valid_access_token"
        mock_check_connection.return_value = True
        mock_validate_input.return_value = "input.csv"
        mock_read_csv.return_value = [{"title": "Example 1"}, {"title": "Example 2"}]
        mock_import_bookmarks.return_value = 2

        args = argparse.Namespace(
            api_token=None,
            client_id="valid_client_id_12345",
            client_secret="valid_client_secret_12345",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False,
        )

        import_to_raindrop(args)

        mock_get_access_token.assert_called_once()
        mock_check_connection.assert_called_once_with("valid_access_token")
        mock_read_csv.assert_called_once()
        mock_import_bookmarks.assert_called_once()

    @patch.object(RaindropApiImporter, "check_api_connection")
    def test_import_to_raindrop_connection_failure_with_api_token(self, mock_check_connection):
        mock_check_connection.return_value = False

        args = argparse.Namespace(
            api_token="valid_token_12345",
            client_id=None,
            client_secret=None,
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False,
        )

        # Should not raise; logs error and returns.
        import_to_raindrop(args)
        mock_check_connection.assert_called_once_with("valid_token_12345")

    @patch.object(RaindropApiImporter, "get_access_token")
    @patch.object(RaindropApiImporter, "check_api_connection")
    def test_import_to_raindrop_connection_failure_with_oauth(
        self, mock_check_connection, mock_get_access_token
    ):
        mock_get_access_token.return_value = "valid_access_token"
        mock_check_connection.return_value = False

        args = argparse.Namespace(
            api_token=None,
            client_id="valid_client_id_12345",
            client_secret="valid_client_secret_12345",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False,
        )

        import_to_raindrop(args)
        mock_get_access_token.assert_called_once()
        mock_check_connection.assert_called_once_with("valid_access_token")

    @patch.object(RaindropApiImporter, "get_access_token")
    def test_import_to_raindrop_oauth_failure_no_fallback(self, mock_get_access_token):
        mock_get_access_token.side_effect = Exception("Failed to get access token")

        args = argparse.Namespace(
            api_token=None,
            client_id="valid_client_id_12345",
            client_secret="valid_client_secret_12345",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False,
        )

        # Should not raise; authentication returns None and the run aborts.
        import_to_raindrop(args)
        mock_get_access_token.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("raindrop_api.api_import.setup_logging")
    @patch("raindrop_api.api_import.import_to_raindrop")
    def test_main_with_api_token(
        self, mock_import_to_raindrop, mock_setup_logging, mock_parse_args
    ):
        mock_args = argparse.Namespace(
            api_token="valid_token",
            client_id=None,
            client_secret=None,
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            log_file="log.txt",
            dry_run=False,
        )
        mock_parse_args.return_value = mock_args

        main()

        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with("log.txt")
        mock_import_to_raindrop.assert_called_once_with(mock_args)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("raindrop_api.api_import.setup_logging")
    @patch("raindrop_api.api_import.import_to_raindrop")
    def test_main_with_oauth(self, mock_import_to_raindrop, mock_setup_logging, mock_parse_args):
        mock_args = argparse.Namespace(
            api_token=None,
            client_id="valid_client_id",
            client_secret="valid_client_secret",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            log_file="log.txt",
            dry_run=False,
        )
        mock_parse_args.return_value = mock_args

        main()

        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with("log.txt")
        mock_import_to_raindrop.assert_called_once_with(mock_args)
