"""
Direct API import functionality for Raindrop.io.

This module provides functionality to import bookmarks directly into Raindrop.io
using their API. It reads bookmarks from a CSV file and sends them to the Raindrop.io API.

API documentation: https://developer.raindrop.io/
OAuth documentation: https://developer.raindrop.io/v1/authentication/token
"""

import argparse
import csv
import time
from typing import Any

import requests
from tqdm import tqdm

from common.logging import get_logger, setup_logging
from common.validation import validate_input_file

# Raindrop.io API endpoints
API_BASE_URL = "https://api.raindrop.io/rest/v1"
RAINDROPS_ENDPOINT = f"{API_BASE_URL}/raindrops"
COLLECTIONS_ENDPOINT = f"{API_BASE_URL}/collections"
TOKEN_ENDPOINT = "https://raindrop.io/oauth/access_token"


def validate_api_token(token: str) -> str:
    """
    Validate the Raindrop.io API token format.

    Parameters
    ----------
    token : str
        The API token to validate.

    Returns
    -------
    str
        The validated API token.

    Raises
    ------
    argparse.ArgumentTypeError
        If the token format is invalid.
    """
    if not token or len(token) < 10:
        raise argparse.ArgumentTypeError("API token is too short or empty")
    return token


def validate_client_credentials(client_id: str, client_secret: str) -> tuple[str, str]:
    """
    Validate the Raindrop.io OAuth client credentials.

    Parameters
    ----------
    client_id : str
        The OAuth client ID to validate.
    client_secret : str
        The OAuth client secret to validate.

    Returns
    -------
    tuple[str, str]
        The validated client ID and client secret.

    Raises
    ------
    argparse.ArgumentTypeError
        If the client credentials are invalid.
    """
    if not client_id or len(client_id) < 10:
        raise argparse.ArgumentTypeError("Client ID is too short or empty")
    if not client_secret or len(client_secret) < 10:
        raise argparse.ArgumentTypeError("Client secret is too short or empty")
    return client_id, client_secret


class RaindropApiImporter:
    """
    Import bookmarks directly into Raindrop.io using their API.

    Encapsulates authentication (OAuth client credentials or legacy API token),
    CSV reading, conversion to Raindrop.io's record schema, and batched upload
    with rate-limit-friendly pacing.
    """

    def __init__(
        self,
        input_file: str,
        collection_id: int = 0,
        batch_size: int = 50,
        api_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        logger=None,
    ):
        """
        Initialize the RaindropApiImporter.

        Parameters
        ----------
        input_file : str
            Path to the CSV file containing bookmarks to import.
        collection_id : int, optional
            Raindrop.io collection ID to import into (default: 0 = Unsorted).
        batch_size : int, optional
            Number of bookmarks to send per API call (default: 50).
        api_token : str | None, optional
            Legacy/deprecated personal API token. Used as fallback if OAuth fails.
        client_id : str | None, optional
            OAuth client ID. Preferred over api_token when set together with
            client_secret.
        client_secret : str | None, optional
            OAuth client secret.
        logger : logging.Logger | None, optional
            Logger instance. If None, one is obtained via get_logger().
        """
        self.input_file = input_file
        self.collection_id = collection_id
        self.batch_size = batch_size
        self.api_token = api_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger = logger or get_logger()

    def get_access_token(self) -> str:
        """
        Get an access token from the Raindrop.io OAuth API.

        Returns
        -------
        str
            The access token.

        Raises
        ------
        Exception
            If the token request fails.
        """
        self.logger.info("Getting access token from Raindrop.io OAuth API")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(TOKEN_ENDPOINT, data=data)

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise Exception("No access token in response")

                self.logger.info("Successfully obtained access token")
                return access_token
            else:
                self.logger.error(
                    f"Failed to get access token: {response.status_code} - {response.text}"
                )
                raise Exception(
                    f"Failed to get access token: {response.status_code} - {response.text}"
                )
        except Exception as e:
            self.logger.exception(f"Error getting access token: {e}")
            raise

    def check_api_connection(self, token: str) -> bool:
        """
        Test the connection to the Raindrop.io API with the given token.

        Named ``check_api_connection`` (not ``test_api_connection``) to prevent
        pytest from collecting it as a test method.

        Parameters
        ----------
        token : str
            The API token (or OAuth access token) to use for authentication.

        Returns
        -------
        bool
            True if the connection is successful, False otherwise.
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(f"{API_BASE_URL}/user", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                self.logger.info(
                    "Connected to Raindrop.io API as user: "
                    f"{user_data.get('user', {}).get('name', 'Unknown')}"
                )
                return True
            else:
                self.logger.error(
                    f"Failed to connect to Raindrop.io API: "
                    f"{response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            self.logger.exception(f"Error connecting to Raindrop.io API: {e}")
            return False

    def get_collections(self, token: str) -> list[dict[str, Any]]:
        """
        Get the list of collections from Raindrop.io.

        Parameters
        ----------
        token : str
            The API token to use for authentication.

        Returns
        -------
        list[dict[str, Any]]
            The list of collections.
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(COLLECTIONS_ENDPOINT, headers=headers)
            if response.status_code == 200:
                collections_data = response.json()
                return collections_data.get("items", [])
            else:
                self.logger.error(
                    f"Failed to get collections: {response.status_code} - {response.text}"
                )
                return []
        except Exception as e:
            self.logger.exception(f"Error getting collections: {e}")
            return []

    def authenticate(self) -> str | None:
        """
        Resolve an access token from the available credentials.

        Prefers OAuth client credentials when both ``client_id`` and
        ``client_secret`` are provided, falling back to ``api_token`` if OAuth
        fails. Returns ``None`` when no credentials are configured.

        Returns
        -------
        str | None
            The access token to use for subsequent API calls, or None if
            authentication is unavailable.
        """
        if self.client_id and self.client_secret:
            try:
                client_id, client_secret = validate_client_credentials(
                    self.client_id, self.client_secret
                )
                # Temporarily store validated values for get_access_token()
                self.client_id, self.client_secret = client_id, client_secret
                token = self.get_access_token()
                self.logger.info("Using OAuth authentication with client credentials")
                return token
            except Exception as e:
                self.logger.error(f"Failed to authenticate with OAuth: {e}")

                if self.api_token:
                    self.logger.info("Falling back to API token authentication")
                    return validate_api_token(self.api_token)

                self.logger.error("No valid authentication method available")
                return None
        elif self.api_token:
            self.logger.warning(
                "Using deprecated API token authentication. Please switch to OAuth authentication."
            )
            return validate_api_token(self.api_token)
        else:
            self.logger.error(
                "No authentication credentials provided. Please provide client ID "
                "and client secret for OAuth authentication."
            )
            return None

    def read_csv(self) -> list[dict[str, str]]:
        """
        Read bookmarks from the configured CSV file.

        Returns
        -------
        list[dict[str, str]]
            The list of bookmarks read from the CSV.
        """
        self.logger.info(f'Reading input file "{self.input_file}"')
        try:
            with open(self.input_file) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except OSError:
            self.logger.exception(f"Failed to read input file: {self.input_file}")
            raise
        except Exception:
            self.logger.exception("Unexpected error while reading input file")
            raise

    def convert_bookmark_to_raindrop(self, bookmark: dict[str, str]) -> dict[str, Any]:
        """
        Convert a bookmark from CSV format to Raindrop.io API format.

        Parameters
        ----------
        bookmark : dict[str, str]
            The bookmark in CSV format.

        Returns
        -------
        dict[str, Any]
            The bookmark in Raindrop.io API format.
        """
        tags: list[str] = []
        if "tags" in bookmark and bookmark["tags"]:
            tags = [tag.strip() for tag in bookmark["tags"].split(",") if tag.strip()]

        raindrop: dict[str, Any] = {
            "link": bookmark.get("url", ""),
            "title": bookmark.get("title", ""),
            "tags": tags,
            "collection": {"$id": self.collection_id},
        }

        if "created" in bookmark and bookmark["created"]:
            try:
                from dateutil import parser

                created_date = parser.parse(bookmark["created"])
                raindrop["created"] = int(created_date.timestamp() * 1000)
            except Exception:
                self.logger.warning(f"Failed to parse created date: {bookmark['created']}")

        return raindrop

    def import_bookmarks(
        self,
        bookmarks: list[dict[str, str]],
        token: str,
        dry_run: bool = False,
    ) -> int:
        """
        Import bookmarks into Raindrop.io.

        Parameters
        ----------
        bookmarks : list[dict[str, str]]
            The list of bookmarks to import.
        token : str
            The API token (or OAuth access token) to use for authentication.
        dry_run : bool, optional
            If True, validate the bookmarks but don't send them to the API.

        Returns
        -------
        int
            The number of bookmarks successfully imported (or that would be
            imported in dry-run mode).
        """
        if not bookmarks:
            self.logger.warning("No bookmarks to import")
            return 0

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        raindrops = [self.convert_bookmark_to_raindrop(bookmark) for bookmark in bookmarks]

        if dry_run:
            self.logger.info(
                f"Dry run: would import {len(raindrops)} bookmarks "
                f"to collection {self.collection_id}"
            )
            return len(raindrops)

        total_bookmarks = len(raindrops)
        successful_imports = 0

        progress_bar = tqdm(total=total_bookmarks, desc="Importing bookmarks", unit="bookmark")

        for i in range(0, total_bookmarks, self.batch_size):
            batch = raindrops[i : i + self.batch_size]

            try:
                response = requests.post(
                    f"{RAINDROPS_ENDPOINT}/multiple",
                    headers=headers,
                    json={"items": batch},
                )

                if response.status_code == 200:
                    result = response.json()
                    imported_count = len(result.get("items", []))
                    successful_imports += imported_count
                    self.logger.info(
                        f"Imported {imported_count} bookmarks (batch {i // self.batch_size + 1})"
                    )
                else:
                    self.logger.error(
                        f"Failed to import batch {i // self.batch_size + 1}: "
                        f"{response.status_code} - {response.text}"
                    )

                progress_bar.update(len(batch))

                # Sleep to avoid rate limiting
                time.sleep(1)

            except Exception as e:
                self.logger.exception(f"Error importing batch {i // self.batch_size + 1}: {e}")

        progress_bar.close()

        return successful_imports

    def run(self, dry_run: bool = False) -> int:
        """
        Run the full import pipeline: authenticate, validate, read, import.

        Parameters
        ----------
        dry_run : bool, optional
            If True, validate without actually sending bookmarks to the API.

        Returns
        -------
        int
            The number of bookmarks imported (0 on early-exit failures).
        """
        token = self.authenticate()
        if not token:
            return 0

        if not self.check_api_connection(token):
            self.logger.error(
                "Failed to connect to Raindrop.io API. "
                "Please check your authentication credentials."
            )
            return 0

        # Validate input file (raises if missing/invalid)
        self.input_file = validate_input_file(self.input_file)

        bookmarks = self.read_csv()
        if not bookmarks:
            self.logger.error("No bookmarks found in the input file")
            return 0

        if dry_run:
            self.logger.info("Dry run mode enabled: validating without sending to API")

        successful_imports = self.import_bookmarks(bookmarks, token, dry_run=dry_run)

        if dry_run:
            self.logger.info(f"Dry run: successfully validated {successful_imports} bookmarks")
        else:
            self.logger.info(f"Successfully imported {successful_imports} bookmarks to Raindrop.io")

        return successful_imports


def import_to_raindrop(args: argparse.Namespace) -> None:
    """
    Plugin shim: construct a RaindropApiImporter from ``args`` and run it.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments.
    """
    # Lazily initialize logging if the caller didn't already do so. This keeps
    # the plugin shim usable from contexts that haven't called setup_logging().
    try:
        logger = get_logger()
    except RuntimeError:
        setup_logging(getattr(args, "log_file", None))
        logger = get_logger()

    importer = RaindropApiImporter(
        input_file=args.input_file,
        collection_id=getattr(args, "collection_id", 0),
        batch_size=getattr(args, "batch_size", 50),
        api_token=getattr(args, "api_token", None),
        client_id=getattr(args, "client_id", None),
        client_secret=getattr(args, "client_secret", None),
        logger=logger,
    )
    importer.run(dry_run=getattr(args, "dry_run", False))


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Import bookmarks directly into Raindrop.io using their API"
    )

    auth_group = parser.add_argument_group("Authentication (OAuth recommended)")
    auth_group.add_argument(
        "--client-id",
        metavar="CLIENT_ID",
        help="Raindrop.io OAuth client ID",
        type=str,
    )
    auth_group.add_argument(
        "--client-secret",
        metavar="CLIENT_SECRET",
        help="Raindrop.io OAuth client secret",
        type=str,
    )
    auth_group.add_argument(
        "--api-token",
        metavar="TOKEN",
        help="Raindrop.io API token (deprecated, use client-id and client-secret instead)",
        type=str,
    )
    parser.add_argument(
        "--input-file",
        metavar="CSVFILE",
        help="Input CSV file path with bookmarks to import",
        type=validate_input_file,
        required=True,
    )
    parser.add_argument(
        "--collection-id",
        metavar="ID",
        help="Raindrop.io collection ID to import into (default: Unsorted)",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--batch-size",
        metavar="SIZE",
        help="Number of bookmarks to import in each batch (default: 50)",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--log-file",
        metavar="LOGFILE",
        help="Log file path (if not specified, logs will only be written to console)",
        type=str,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports without sending to API",
    )

    args = parser.parse_args()

    setup_logging(getattr(args, "log_file", None))
    import_to_raindrop(args)


if __name__ == "__main__":
    main()
