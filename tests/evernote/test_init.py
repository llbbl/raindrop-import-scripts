import pytest
import argparse
from unittest.mock import patch, MagicMock
from evernote import EvernoteImportPlugin


class TestEvernoteImportPlugin:
    """Tests for the EvernoteImportPlugin class."""

    def test_get_name(self):
        """Test that get_name returns the correct name."""
        assert EvernoteImportPlugin.get_name() == "evernote"

    def test_get_description(self):
        """Test that get_description returns a non-empty description."""
        description = EvernoteImportPlugin.get_description()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_create_parser(self):
        """Test that create_parser creates a parser with the expected arguments."""
        parser = EvernoteImportPlugin.create_parser()
        
        # Check that the parser has the expected description
        assert parser.description == EvernoteImportPlugin.get_description()
        
        # Check that the parser has the expected arguments
        arguments = {action.dest: action for action in parser._actions}
        assert "input_file" in arguments
        assert "output_file" in arguments
        assert "log_file" in arguments
        assert "use_markdown" in arguments
        
        # Check that the required arguments are marked as required
        assert arguments["input_file"].required
        assert arguments["output_file"].required
        assert not arguments["log_file"].required
        assert not arguments["use_markdown"].required
        
        # Check that the input file argument has the correct metavar and help
        assert arguments["input_file"].metavar == "ENEXFILE"
        assert "Input ENEX file path" in arguments["input_file"].help

    @patch("evernote.convert_enex")
    def test_convert(self, mock_convert_enex):
        """Test that convert calls convert_enex with the correct arguments."""
        # Create mock args
        args = argparse.Namespace(
            input_file="input.enex",
            output_file="output.csv",
            use_markdown=True
        )
        
        # Call convert
        EvernoteImportPlugin.convert(args)
        
        # Check that convert_enex was called with the correct arguments
        mock_convert_enex.assert_called_once_with(args)