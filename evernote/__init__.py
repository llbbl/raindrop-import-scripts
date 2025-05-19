"""
Evernote import plugin for Raindrop.io.

This module provides a plugin for importing Evernote ENEX files into Raindrop.io.
"""

import argparse
from typing import List

from common.cli import create_base_parser, parse_args
from common.plugins import BaseImportPlugin, register_plugin
from evernote.enex2csv import convert_enex


@register_plugin
class EvernoteImportPlugin(BaseImportPlugin):
    """
    Plugin for importing Evernote ENEX files into Raindrop.io.
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
        return "evernote"
    
    @classmethod
    def get_description(cls) -> str:
        """
        Get a description of the import source.
        
        Returns
        -------
        str
            A description of the import source.
        """
        return "Convert Evernote ENEX file to CSV for import into Raindrop.io"
    
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
        parser.add_argument(
            "--use-markdown",
            help="Convert note content to Markdown",
            action="store_true",
        )
        
        # Update the metavar for input-file to be more specific
        parser._option_string_actions["--input-file"].metavar = "ENEXFILE"
        parser._option_string_actions["--input-file"].help = "Input ENEX file path"
        
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
        convert_enex(args)