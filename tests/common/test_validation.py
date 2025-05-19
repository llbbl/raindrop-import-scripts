import os
import pytest
import tempfile
import argparse
from common.validation import validate_input_file, validate_output_file


class TestValidation:
    """Tests for the validation module."""

    def test_validate_input_file_exists(self):
        """Test that validate_input_file accepts a file that exists."""
        with tempfile.NamedTemporaryFile() as temp_file:
            # The file exists, so this should return the path without raising an exception
            assert validate_input_file(temp_file.name) == temp_file.name

    def test_validate_input_file_not_exists(self):
        """Test that validate_input_file raises an exception for a file that doesn't exist."""
        with pytest.raises(argparse.ArgumentTypeError) as excinfo:
            validate_input_file("/path/to/nonexistent/file")
        assert "Input file does not exist" in str(excinfo.value)

    def test_validate_input_file_not_a_file(self):
        """Test that validate_input_file raises an exception for a path that's not a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(argparse.ArgumentTypeError) as excinfo:
                validate_input_file(temp_dir)
            assert "Input path is not a file" in str(excinfo.value)

    def test_validate_input_file_not_readable(self, monkeypatch):
        """Test that validate_input_file raises an exception for a file that's not readable."""
        with tempfile.NamedTemporaryFile() as temp_file:
            # Mock os.access to return False for read access
            monkeypatch.setattr(os, "access", lambda path, mode: False if mode == os.R_OK else True)
            
            with pytest.raises(argparse.ArgumentTypeError) as excinfo:
                validate_input_file(temp_file.name)
            assert "Input file is not readable" in str(excinfo.value)

    def test_validate_output_file_directory_exists(self):
        """Test that validate_output_file accepts a path in a directory that exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output.csv")
            assert validate_output_file(output_path) == output_path

    def test_validate_output_file_directory_not_exists(self):
        """Test that validate_output_file raises an exception for a path in a directory that doesn't exist."""
        with pytest.raises(argparse.ArgumentTypeError) as excinfo:
            validate_output_file("/path/to/nonexistent/directory/output.csv")
        assert "Output directory does not exist" in str(excinfo.value)

    def test_validate_output_file_directory_not_writable(self, monkeypatch):
        """Test that validate_output_file raises an exception for a path in a directory that's not writable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock os.access to return False for write access
            monkeypatch.setattr(os, "access", lambda path, mode: False if mode == os.W_OK else True)
            
            output_path = os.path.join(temp_dir, "output.csv")
            with pytest.raises(argparse.ArgumentTypeError) as excinfo:
                validate_output_file(output_path)
            assert "Output directory is not writable" in str(excinfo.value)

    def test_validate_output_file_current_directory(self):
        """Test that validate_output_file accepts a path in the current directory."""
        # This should work as long as the current directory exists and is writable
        assert validate_output_file("output.csv") == "output.csv"