import sys
import pytest
import argparse
from common.cli import create_base_parser, parse_args


class TestCLI:
    """Tests for the CLI module."""

    def test_create_base_parser(self):
        """Test that create_base_parser creates a parser with the expected arguments."""
        description = "Test description"
        parser = create_base_parser(description)
        
        # Check that the parser has the expected description
        assert parser.description == description
        
        # Check that the parser has the expected arguments
        arguments = {action.dest: action for action in parser._actions}
        assert "input_file" in arguments
        assert "output_file" in arguments
        assert "log_file" in arguments
        
        # Check that the required arguments are marked as required
        assert arguments["input_file"].required
        assert arguments["output_file"].required
        assert not arguments["log_file"].required

    def test_parse_args_with_args(self):
        """Test that parse_args correctly parses provided arguments."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--test-arg", type=str)
        
        # Test with provided arguments
        args = parse_args(parser, ["--test-arg", "test-value"])
        assert args.test_arg == "test-value"

    def test_parse_args_without_args(self, monkeypatch):
        """Test that parse_args correctly uses sys.argv when no arguments are provided."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--test-arg", type=str)
        
        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", ["script.py", "--test-arg", "test-value"])
        
        # Test without providing arguments (should use sys.argv)
        args = parse_args(parser)
        assert args.test_arg == "test-value"

    def test_parse_args_with_validation(self, monkeypatch):
        """Test that parse_args correctly uses the validation functions."""
        # Create a parser with input and output file arguments
        parser = create_base_parser("Test description")
        
        # Create temporary files for testing
        import tempfile
        with tempfile.NamedTemporaryFile() as input_file, tempfile.TemporaryDirectory() as output_dir:
            output_file = f"{output_dir}/output.csv"
            
            # Test with valid arguments
            args = parse_args(parser, ["--input-file", input_file.name, "--output-file", output_file])
            assert args.input_file == input_file.name
            assert args.output_file == output_file
            
            # Test with invalid input file
            with pytest.raises(SystemExit):
                parse_args(parser, ["--input-file", "/nonexistent/file", "--output-file", output_file])
            
            # Test with invalid output directory
            with pytest.raises(SystemExit):
                parse_args(parser, ["--input-file", input_file.name, "--output-file", "/nonexistent/dir/file.csv"])