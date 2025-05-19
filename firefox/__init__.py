"""
Firefox bookmarks import plugin for Raindrop.io.

This module provides a plugin for importing Firefox bookmarks JSON export files into Raindrop.io.
"""

import argparse
from typing import List

from common.cli import create_base_parser, parse_args
from common.plugins import BaseImportPlugin, register_plugin
from common.logging import get_logger
from firefox.firefox2csv import FirefoxBookmarkConverter


@register_plugin
class FirefoxImportPlugin(BaseImportPlugin):
    """
    Plugin for importing Firefox bookmarks JSON export files into Raindrop.io.
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
        return "firefox"
    
    @classmethod
    def get_description(cls) -> str:
        """
        Get a description of the import source.
        
        Returns
        -------
        str
            A description of the import source.
        """
        return "Convert Firefox bookmarks JSON file to CSV for import into Raindrop.io"
    
    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """
        Create an argument parser for this import source.
        
        Returns
        -------
        argparse.ArgumentParser
            An argument parser configured for this import source.
        """
        parser = create_base_parser(cls.get_description())
        
        # Update the metavar for input-file to be more specific
        parser._option_string_actions["--input-file"].metavar = "JSONFILE"
        parser._option_string_actions["--input-file"].help = "Input JSON file path (exported from Firefox bookmarks)"
        
        return parser
    
    @classmethod
    def convert(cls, args: argparse.Namespace) -> None:
        """
        Convert the input file to CSV format.
        
        Parameters
        ----------
        args : argparse.Namespace
            Parsed command line arguments.
        
        Returns
        -------
        None
            The function processes files and doesn't return a value.
        """
        converter = FirefoxBookmarkConverter(args.input_file, args.output_file, get_logger())
        converter.convert(
            field_mappings=args.field_mappings,
            preview=args.preview,
            preview_limit=args.preview_limit,
            dry_run=args.dry_run
        )