import sys
import pytest
import argparse
from unittest.mock import patch, MagicMock
from raindrop_import import create_main_parser, main


class TestRaindropImport:
    """Tests for the raindrop_import module."""

    def test_create_main_parser(self):
        """Test that create_main_parser creates a parser with the expected arguments."""
        parser = create_main_parser()
        
        # Check that the parser has the expected description
        assert "Import data from various sources into Raindrop.io" in parser.description
        
        # Check that the parser has the expected arguments
        arguments = {action.dest: action for action in parser._actions}
        assert "log_file" in arguments
        assert "config_file" in arguments
        assert "dry_run" in arguments
        
        # Check that none of the arguments are required
        assert not arguments["log_file"].required
        assert not arguments["config_file"].required
        assert not arguments["dry_run"].required

    @patch("raindrop_import.PluginRegistry.discover_plugins")
    @patch("raindrop_import.PluginRegistry.get_all_plugins")
    @patch("raindrop_import.create_main_parser")
    @patch("raindrop_import.setup_logging")
    @patch("raindrop_import.get_logger")
    @patch("raindrop_import.load_config")
    @patch("raindrop_import.apply_config_to_args")
    def test_main_no_plugins(self, mock_apply_config, mock_load_config, mock_get_logger, 
                            mock_setup_logging, mock_create_parser, mock_get_plugins, 
                            mock_discover_plugins):
        """Test that main exits when no plugins are found."""
        # Set up mocks
        mock_get_plugins.return_value = {}
        
        # Call main with empty args
        with pytest.raises(SystemExit) as excinfo:
            main([])
        
        # Check that the script exited with code 1
        assert excinfo.value.code == 1
        
        # Check that the functions were called
        mock_discover_plugins.assert_called_once()
        mock_get_plugins.assert_called_once()
        mock_create_parser.assert_not_called()

    @patch("raindrop_import.PluginRegistry.discover_plugins")
    @patch("raindrop_import.PluginRegistry.get_all_plugins")
    @patch("raindrop_import.PluginRegistry.get_plugin")
    @patch("raindrop_import.create_main_parser")
    @patch("raindrop_import.setup_logging")
    @patch("raindrop_import.get_logger")
    @patch("raindrop_import.load_config")
    @patch("raindrop_import.apply_config_to_args")
    def test_main_unknown_source(self, mock_apply_config, mock_load_config, mock_get_logger, 
                                mock_setup_logging, mock_create_parser, mock_get_plugin, 
                                mock_get_plugins, mock_discover_plugins):
        """Test that main exits when an unknown source is specified."""
        # Set up mocks
        mock_plugin = MagicMock()
        mock_get_plugins.return_value = {"mock": mock_plugin}
        mock_get_plugin.return_value = None
        
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        
        mock_args = argparse.Namespace(
            source="unknown",
            log_file=None,
            config_file=None
        )
        mock_parser.parse_args.return_value = mock_args
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call main with unknown source
        with pytest.raises(SystemExit) as excinfo:
            main(["unknown"])
        
        # Check that the script exited with code 1
        assert excinfo.value.code == 1
        
        # Check that the functions were called
        mock_discover_plugins.assert_called_once()
        mock_get_plugins.assert_called_once()
        mock_create_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with(None)
        mock_get_logger.assert_called_once()
        mock_load_config.assert_called_once_with(None)
        mock_apply_config.assert_called_once()
        mock_get_plugin.assert_called_once_with("unknown")
        mock_logger.error.assert_called_once()

    @patch("raindrop_import.PluginRegistry.discover_plugins")
    @patch("raindrop_import.PluginRegistry.get_all_plugins")
    @patch("raindrop_import.PluginRegistry.get_plugin")
    @patch("raindrop_import.create_main_parser")
    @patch("raindrop_import.setup_logging")
    @patch("raindrop_import.get_logger")
    @patch("raindrop_import.load_config")
    @patch("raindrop_import.apply_config_to_args")
    def test_main_success(self, mock_apply_config, mock_load_config, mock_get_logger, 
                        mock_setup_logging, mock_create_parser, mock_get_plugin, 
                        mock_get_plugins, mock_discover_plugins):
        """Test that main successfully calls the plugin's convert method."""
        # Set up mocks
        mock_plugin = MagicMock()
        mock_get_plugins.return_value = {"mock": mock_plugin}
        mock_get_plugin.return_value = mock_plugin
        
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        
        mock_args = argparse.Namespace(
            source="mock",
            log_file="log.txt",
            config_file="config.yaml"
        )
        mock_parser.parse_args.return_value = mock_args
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_config = {"global": {"dry_run": True}}
        mock_load_config.return_value = mock_config
        
        mock_apply_config.return_value = mock_args
        
        # Call main with mock source
        main(["mock"])
        
        # Check that the functions were called
        mock_discover_plugins.assert_called_once()
        mock_get_plugins.assert_called_once()
        mock_create_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with("log.txt")
        mock_get_logger.assert_called_once()
        mock_load_config.assert_called_once_with("config.yaml")
        mock_apply_config.assert_called_once_with(mock_args, mock_config)
        mock_get_plugin.assert_called_once_with("mock")
        mock_plugin.convert.assert_called_once_with(mock_args)
        mock_logger.info.assert_called()

    @patch("raindrop_import.PluginRegistry.discover_plugins")
    @patch("raindrop_import.PluginRegistry.get_all_plugins")
    @patch("raindrop_import.PluginRegistry.get_plugin")
    @patch("raindrop_import.create_main_parser")
    @patch("raindrop_import.setup_logging")
    @patch("raindrop_import.get_logger")
    @patch("raindrop_import.load_config")
    @patch("raindrop_import.apply_config_to_args")
    def test_main_convert_error(self, mock_apply_config, mock_load_config, mock_get_logger, 
                                mock_setup_logging, mock_create_parser, mock_get_plugin, 
                                mock_get_plugins, mock_discover_plugins):
        """Test that main handles errors from the plugin's convert method."""
        # Set up mocks
        mock_plugin = MagicMock()
        mock_plugin.convert.side_effect = Exception("Convert error")
        mock_get_plugins.return_value = {"mock": mock_plugin}
        mock_get_plugin.return_value = mock_plugin
        
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        
        mock_args = argparse.Namespace(
            source="mock",
            log_file=None,
            config_file=None
        )
        mock_parser.parse_args.return_value = mock_args
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_config = {}
        mock_load_config.return_value = mock_config
        
        mock_apply_config.return_value = mock_args
        
        # Call main with mock source that raises an error
        with pytest.raises(SystemExit) as excinfo:
            main(["mock"])
        
        # Check that the script exited with code 1
        assert excinfo.value.code == 1
        
        # Check that the functions were called
        mock_discover_plugins.assert_called_once()
        mock_get_plugins.assert_called_once()
        mock_create_parser.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with(None)
        mock_get_logger.assert_called_once()
        mock_load_config.assert_called_once_with(None)
        mock_apply_config.assert_called_once_with(mock_args, mock_config)
        mock_get_plugin.assert_called_once_with("mock")
        mock_plugin.convert.assert_called_once_with(mock_args)
        mock_logger.exception.assert_called_once()