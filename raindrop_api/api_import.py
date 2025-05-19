"""
Direct API import functionality for Raindrop.io.

This module provides functionality to import bookmarks directly into Raindrop.io
using their API. It reads bookmarks from a CSV file and sends them to the Raindrop.io API.

API documentation: https://developer.raindrop.io/
"""

import argparse
import csv
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional
import requests
from tqdm import tqdm

from common.logging import setup_logging, get_logger
from common.validation import validate_input_file

# Define logger at module level but don't initialize it yet
logger = None

# Raindrop.io API endpoints
API_BASE_URL = "https://api.raindrop.io/rest/v1"
RAINDROPS_ENDPOINT = f"{API_BASE_URL}/raindrops"
COLLECTIONS_ENDPOINT = f"{API_BASE_URL}/collections"


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


def test_api_connection(token: str) -> bool:
    """
    Test the connection to the Raindrop.io API.

    Parameters
    ----------
    token : str
        The API token to use for authentication.

    Returns
    -------
    bool
        True if the connection is successful, False otherwise.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{API_BASE_URL}/user", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Connected to Raindrop.io API as user: {user_data.get('user', {}).get('name', 'Unknown')}")
            return True
        else:
            logger.error(f"Failed to connect to Raindrop.io API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.exception(f"Error connecting to Raindrop.io API: {e}")
        return False


def get_collections(token: str) -> List[Dict[str, Any]]:
    """
    Get the list of collections from Raindrop.io.

    Parameters
    ----------
    token : str
        The API token to use for authentication.

    Returns
    -------
    List[Dict[str, Any]]
        The list of collections.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(COLLECTIONS_ENDPOINT, headers=headers)
        if response.status_code == 200:
            collections_data = response.json()
            return collections_data.get("items", [])
        else:
            logger.error(f"Failed to get collections: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.exception(f"Error getting collections: {e}")
        return []


def read_csv_file(file_path: str) -> List[Dict[str, str]]:
    """
    Read bookmarks from a CSV file.

    Parameters
    ----------
    file_path : str
        Path to the CSV file.

    Returns
    -------
    List[Dict[str, str]]
        The list of bookmarks.
    """
    logger.info(f'Reading input file "{file_path}"')
    try:
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except IOError:
        logger.exception(f"Failed to read input file: {file_path}")
        raise
    except Exception:
        logger.exception("Unexpected error while reading input file")
        raise


def convert_bookmark_to_raindrop(bookmark: Dict[str, str], collection_id: int) -> Dict[str, Any]:
    """
    Convert a bookmark from CSV format to Raindrop.io API format.

    Parameters
    ----------
    bookmark : Dict[str, str]
        The bookmark in CSV format.
    collection_id : int
        The ID of the collection to import into.

    Returns
    -------
    Dict[str, Any]
        The bookmark in Raindrop.io API format.
    """
    # Extract tags from the tags field (comma-separated)
    tags = []
    if "tags" in bookmark and bookmark["tags"]:
        tags = [tag.strip() for tag in bookmark["tags"].split(",") if tag.strip()]
    
    # Create the raindrop object
    raindrop = {
        "link": bookmark.get("url", ""),
        "title": bookmark.get("title", ""),
        "tags": tags,
        "collection": {
            "$id": collection_id
        }
    }
    
    # Add created date if available
    if "created" in bookmark and bookmark["created"]:
        try:
            # Try to parse the date in various formats
            from dateutil import parser
            created_date = parser.parse(bookmark["created"])
            raindrop["created"] = int(created_date.timestamp() * 1000)  # Convert to milliseconds
        except Exception:
            logger.warning(f"Failed to parse created date: {bookmark['created']}")
    
    return raindrop


def import_bookmarks(bookmarks: List[Dict[str, str]], token: str, collection_id: int, batch_size: int, dry_run: bool) -> int:
    """
    Import bookmarks into Raindrop.io.

    Parameters
    ----------
    bookmarks : List[Dict[str, str]]
        The list of bookmarks to import.
    token : str
        The API token to use for authentication.
    collection_id : int
        The ID of the collection to import into.
    batch_size : int
        The number of bookmarks to import in each batch.
    dry_run : bool
        If True, validate the bookmarks but don't send them to the API.

    Returns
    -------
    int
        The number of bookmarks successfully imported.
    """
    if not bookmarks:
        logger.warning("No bookmarks to import")
        return 0
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Convert bookmarks to Raindrop.io format
    raindrops = [convert_bookmark_to_raindrop(bookmark, collection_id) for bookmark in bookmarks]
    
    if dry_run:
        logger.info(f"Dry run: would import {len(raindrops)} bookmarks to collection {collection_id}")
        return len(raindrops)
    
    # Import bookmarks in batches
    total_bookmarks = len(raindrops)
    successful_imports = 0
    
    # Initialize progress bar
    progress_bar = tqdm(total=total_bookmarks, desc="Importing bookmarks", unit="bookmark")
    
    for i in range(0, total_bookmarks, batch_size):
        batch = raindrops[i:i+batch_size]
        
        try:
            # Import the batch
            response = requests.post(
                f"{RAINDROPS_ENDPOINT}/multiple",
                headers=headers,
                json={"items": batch}
            )
            
            if response.status_code == 200:
                result = response.json()
                imported_count = len(result.get("items", []))
                successful_imports += imported_count
                logger.info(f"Imported {imported_count} bookmarks (batch {i//batch_size + 1})")
            else:
                logger.error(f"Failed to import batch {i//batch_size + 1}: {response.status_code} - {response.text}")
            
            # Update progress bar
            progress_bar.update(len(batch))
            
            # Sleep to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            logger.exception(f"Error importing batch {i//batch_size + 1}: {e}")
            # Continue with next batch
    
    # Close progress bar
    progress_bar.close()
    
    return successful_imports


def import_to_raindrop(args: argparse.Namespace) -> None:
    """
    Import bookmarks directly into Raindrop.io using their API.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments.

    Returns
    -------
    None
        The function imports bookmarks and doesn't return a value.
    """
    global logger
    # Initialize logger if it's not already initialized
    if logger is None:
        try:
            logger = get_logger()
        except RuntimeError:
            # If setup_logging hasn't been called yet, call it now
            setup_logging(getattr(args, 'log_file', None))
            logger = get_logger()
    
    # Validate API token
    token = validate_api_token(args.api_token)
    
    # Test API connection
    if not test_api_connection(token):
        logger.error("Failed to connect to Raindrop.io API. Please check your API token.")
        return
    
    # Validate input file
    input_file = validate_input_file(args.input_file)
    
    # Read bookmarks from CSV file
    bookmarks = read_csv_file(input_file)
    
    if not bookmarks:
        logger.error("No bookmarks found in the input file")
        return
    
    # Get collection ID
    collection_id = args.collection_id
    
    # Check if dry-run mode is enabled
    dry_run = getattr(args, 'dry_run', False)
    if dry_run:
        logger.info("Dry run mode enabled: validating without sending to API")
    
    # Get batch size
    batch_size = args.batch_size
    
    # Import bookmarks
    successful_imports = import_bookmarks(bookmarks, token, collection_id, batch_size, dry_run)
    
    if dry_run:
        logger.info(f"Dry run: successfully validated {successful_imports} bookmarks")
    else:
        logger.info(f"Successfully imported {successful_imports} bookmarks to Raindrop.io")


def main() -> None:
    """
    Main entry point for the script.

    Returns
    -------
    None
    """
    global logger
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Import bookmarks directly into Raindrop.io using their API")
    
    # Add arguments
    parser.add_argument(
        "--api-token",
        metavar="TOKEN",
        help="Raindrop.io API token",
        type=str,
        required=True,
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
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_file)
    logger = get_logger()
    
    # Import bookmarks
    import_to_raindrop(args)


if __name__ == "__main__":
    main()