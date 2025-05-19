import pytest
import argparse
from unittest.mock import patch, MagicMock
from pocket import PocketImportPlugin


class TestPocketImportPlugin:
    """Tests for the PocketImportPlugin class."""

    def test_get_name(self):
        """Test that get_name returns the correct name."""
        assert PocketImportPlugin.get_name() == "pocket"

    def test_get_description(self):
        """Test that get_description returns a non-empty description."""
        description = PocketImportPlugin.get_description()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_create_parser(self):
        """Test that create_parser creates a parser with the expected arguments."""
        parser = PocketImportPlugin.create_parser()
        
        # Check that the parser has the expected description
        assert parser.description == PocketImportPlugin.get_description()
        
        # Check that the parser has the expected arguments
        arguments = {action.dest: action for action in parser._actions}
        assert "input_file" in arguments
        assert "output_file" in arguments
        assert "log_file" in arguments
        
        # Check that the required arguments are marked as required
        assert arguments["input_file"].required
        assert arguments["output_file"].required
        assert not arguments["log_file"].required
        
        # Check that the input file argument has the correct metavar and help
        assert arguments["input_file"].metavar == "HTMLFILE"
        assert "Input HTML file path" in arguments["input_file"].help

    @patch("pocket.convert_html")
    def test_convert(self, mock_convert_html):
        """Test that convert calls convert_html with the correct arguments."""
        # Create mock args
        args = argparse.Namespace(
            input_file="input.html",
            output_file="output.csv"
        )
        
        # Call convert
        PocketImportPlugin.convert(args)
        
        # Check that convert_html was called with the correct arguments
        mock_convert_html.assert_called_once_with(args)