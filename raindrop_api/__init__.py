"""
Raindrop.io API import plugin.

This module provides a plugin for directly importing bookmarks into Raindrop.io using their API.
"""

import argparse
from typing import List, Optional

from common.cli import create_base_parser, parse_args
from common.plugins import BaseImportPlugin, register_plugin
from raindrop_api.api_import import import_to_raindrop


@register_plugin
class RaindropApiImportPlugin(BaseImportPlugin):
    """
    Plugin for directly importing bookmarks into Raindrop.io using their API.
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Get the name of the import source.

        Returns
        -------
        str
            The name of the import source.
        """
        return "raindrop-api"

    @classmethod
    def get_description(cls) -> str:
        """
        Get a description of the import source.

        Returns
        -------
        str
            A description of the import source.
        """
        return "Import bookmarks directly into Raindrop.io using their API"

    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """
        Create an argument parser for this import source.

        Returns
        -------
        argparse.ArgumentParser
            An argument parser configured for this import source.
        """
        parser = argparse.ArgumentParser(description=cls.get_description(), add_help=False)

        # Add API-specific arguments
        parser.add_argument(
            "--client-id",
            metavar="CLIENT_ID",
            help="Raindrop.io OAuth client ID",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--client-secret",
            metavar="CLIENT_SECRET",
            help="Raindrop.io OAuth client secret",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--api-token",
            metavar="TOKEN",
            help="Raindrop.io API token (deprecated, use client-id and client-secret instead)",
            type=str,
            required=False,
        )
        parser.add_argument(
            "--input-file",
            metavar="CSVFILE",
            help="Input CSV file path with bookmarks to import",
            type=str,
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

        return parser

    @classmethod
    def convert(cls, args: argparse.Namespace) -> None:
        """
        Import bookmarks directly into Raindrop.io using their API.

        Parameters
        ----------
        args : argparse.Namespace
            Parsed command line arguments.

        Returns
        -------
        None
            The function imports bookmarks and doesn't return a value.
        """
        import_to_raindrop(args)
