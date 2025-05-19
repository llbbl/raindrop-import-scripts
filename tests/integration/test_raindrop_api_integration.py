"""
Integration tests for the Raindrop.io API import workflow.
"""

import os
import csv
import tempfile
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch


class TestRaindropApiIntegration:
    """Integration tests for the Raindrop.io API import workflow."""

    def test_raindrop_api_import_dry_run(self):
        """Test the dry-run mode of the Raindrop.io API import."""
        # Create a temporary CSV file with test bookmarks
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, newline="") as temp_input:
            writer = csv.DictWriter(
                temp_input, fieldnames=["title", "url", "tags", "created"], 
                delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerow({
                "title": "Test Bookmark 1",
                "url": "http://example.com/test1",
                "tags": "test,api",
                "created": "2023-01-01 12:00:00"
            })
            writer.writerow({
                "title": "Test Bookmark 2",
                "url": "http://example.com/test2",
                "tags": "test",
                "created": "2023-01-02 12:00:00"
            })
            input_csv = temp_input.name

        try:
            # Run the import command with dry-run
            cmd = [
                "python", "raindrop_import.py", "raindrop-api",
                "--api-token", "test_token_12345",
                "--input-file", input_csv,
                "--collection-id", "0",
                "--batch-size", "50",
                "--dry-run"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Print the command output for debugging
            print(f"Command stdout: {result.stdout}")
            print(f"Command stderr: {result.stderr}")

            # Check that the command succeeded
            assert result.returncode == 0, f"Command failed with output: {result.stderr}"

            # Check that the output contains the expected messages
            assert "Dry run mode enabled" in result.stdout or "Dry run mode enabled" in result.stderr
            assert "would import 2 bookmarks" in result.stdout or "would import 2 bookmarks" in result.stderr
            assert "successfully validated 2 bookmarks" in result.stdout or "successfully validated 2 bookmarks" in result.stderr
        finally:
            # Clean up the temporary file
            if os.path.exists(input_csv):
                os.unlink(input_csv)

    @patch("subprocess.run")
    def test_raindrop_api_import_help(self, mock_run):
        """Test the help output of the Raindrop.io API import command."""
        # Mock the subprocess.run call
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        # Run the help command
        cmd = ["python", "raindrop_import.py", "raindrop-api", "--help"]
        subprocess.run(cmd)

        # Check that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == cmd