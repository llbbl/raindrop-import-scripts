import os
import pytest
import tempfile
import argparse
import yaml
from common.config import get_config_file_path, load_config, apply_config_to_args


class TestConfig:
    """Tests for the config module."""

    def test_get_config_file_path_current_dir(self, monkeypatch):
        """Test that get_config_file_path finds a config file in the current directory."""
        # Create a temporary file in the current directory
        with tempfile.NamedTemporaryFile(dir=".", prefix="raindrop_import", suffix=".yaml") as temp_file:
            # Rename the file to raindrop_import.yaml
            original_name = temp_file.name
            new_name = "raindrop_import.yaml"
            os.rename(original_name, new_name)
            
            try:
                # Test that the function finds the file
                assert get_config_file_path() == new_name
            finally:
                # Clean up
                os.remove(new_name)

    def test_get_config_file_path_home_dir(self, monkeypatch):
        """Test that get_config_file_path finds a config file in the home directory."""
        # Mock os.path.exists to return True for ~/.raindrop_import.yaml and False for ./raindrop_import.yaml
        def mock_exists(path):
            return path == os.path.expanduser("~/.raindrop_import.yaml")
        
        monkeypatch.setattr(os.path, "exists", mock_exists)
        
        # Test that the function finds the file
        assert get_config_file_path() == os.path.expanduser("~/.raindrop_import.yaml")

    def test_get_config_file_path_not_found(self, monkeypatch):
        """Test that get_config_file_path returns an empty string when no config file is found."""
        # Mock os.path.exists to return False for all paths
        monkeypatch.setattr(os.path, "exists", lambda path: False)
        
        # Test that the function returns an empty string
        assert get_config_file_path() == ""

    def test_load_config_with_file(self):
        """Test that load_config correctly loads a config file."""
        # Create a temporary config file
        config_data = {
            "global": {
                "log_file": "global.log"
            },
            "evernote": {
                "use_markdown": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file.flush()
            
            # Test that the function loads the config
            config = load_config(temp_file.name)
            assert config == config_data

    def test_load_config_without_file(self, monkeypatch):
        """Test that load_config returns an empty dict when no config file is provided or found."""
        # Mock get_config_file_path to return an empty string
        monkeypatch.setattr("common.config.get_config_file_path", lambda: "")
        
        # Test that the function returns an empty dict
        assert load_config() == {}

    def test_load_config_invalid_file(self):
        """Test that load_config handles invalid config files gracefully."""
        # Create a temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            temp_file.write("invalid: yaml: content:")
            temp_file.flush()
            
            # Test that the function returns an empty dict
            assert load_config(temp_file.name) == {}

    def test_load_config_non_dict(self):
        """Test that load_config handles non-dict config files gracefully."""
        # Create a temporary file with non-dict YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as temp_file:
            yaml.dump(["item1", "item2"], temp_file)
            temp_file.flush()
            
            # Test that the function returns an empty dict
            assert load_config(temp_file.name) == {}

    def test_apply_config_to_args(self):
        """Test that apply_config_to_args correctly applies config settings to args."""
        # Create a config dict
        config = {
            "global": {
                "log_file": "global.log",
                "dry_run": True
            },
            "evernote": {
                "use_markdown": True,
                "log_file": "evernote.log"  # This should override the global setting
            }
        }
        
        # Create args
        args = argparse.Namespace(
            source="evernote",
            input_file="input.enex",
            output_file="output.csv",
            log_file=None,  # This should be filled from config
            use_markdown=None  # This should be filled from config
        )
        
        # Apply config to args
        updated_args = apply_config_to_args(args, config)
        
        # Check that the args were updated correctly
        assert updated_args.log_file == "evernote.log"  # Source-specific setting overrides global
        assert updated_args.use_markdown is True
        assert updated_args.dry_run is True
        
        # Check that the original args weren't modified
        assert args is updated_args

    def test_apply_config_to_args_no_override(self):
        """Test that apply_config_to_args doesn't override explicitly provided args."""
        # Create a config dict
        config = {
            "global": {
                "log_file": "global.log"
            },
            "evernote": {
                "use_markdown": True
            }
        }
        
        # Create args with explicitly provided values
        args = argparse.Namespace(
            source="evernote",
            input_file="input.enex",
            output_file="output.csv",
            log_file="explicit.log",  # This should not be overridden
            use_markdown=False  # This should not be overridden
        )
        
        # Apply config to args
        updated_args = apply_config_to_args(args, config)
        
        # Check that the explicitly provided args weren't overridden
        assert updated_args.log_file == "explicit.log"
        assert updated_args.use_markdown is False