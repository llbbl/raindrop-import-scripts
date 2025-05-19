"""
Tests for the raindrop_api.__init__ module.
"""

import pytest
import argparse
from unittest.mock import patch, MagicMock
from raindrop_api import RaindropApiImportPlugin


class TestRaindropApiImportPlugin:
    """Tests for the RaindropApiImportPlugin class."""

    def test_get_name(self):
        """Test that get_name returns the correct name."""
        assert RaindropApiImportPlugin.get_name() == "raindrop-api"

    def test_get_description(self):
        """Test that get_description returns a non-empty description."""
        description = RaindropApiImportPlugin.get_description()
        assert description
        assert isinstance(description, str)

    def test_create_parser(self):
        """Test that create_parser returns a parser with the expected arguments."""
        parser = RaindropApiImportPlugin.create_parser()
        
        # Check that the parser has the expected arguments
        actions = {action.dest: action for action in parser._actions}
        
        assert "api_token" in actions
        assert actions["api_token"].required is True
        
        assert "input_file" in actions
        assert actions["input_file"].required is True
        
        assert "collection_id" in actions
        assert actions["collection_id"].default == 0
        
        assert "batch_size" in actions
        assert actions["batch_size"].default == 50
        
        assert "log_file" in actions
        assert actions["log_file"].required is False
        
        assert "dry_run" in actions
        assert isinstance(actions["dry_run"], argparse._StoreTrueAction)

    @patch("raindrop_api.import_to_raindrop")
    def test_convert(self, mock_import_to_raindrop):
        """Test that convert calls import_to_raindrop with the correct arguments."""
        # Create args
        args = argparse.Namespace(
            api_token="valid_token",
            input_file="input.csv",
            collection_id=1,
            batch_size=50,
            dry_run=False
        )
        
        # Call convert
        RaindropApiImportPlugin.convert(args)
        
        # Check that import_to_raindrop was called with the correct arguments
        mock_import_to_raindrop.assert_called_once_with(args)